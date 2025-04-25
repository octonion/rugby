import pandas as pd
import numpy as np
import sqlalchemy
# import statsmodels.formula.api as smf # No longer needed for model fitting
# import statsmodels.api as sm # No longer needed for model fitting
import logging
import os
from datetime import datetime

# --- Import Pymer4 ---
# Ensure R and lme4 are installed for this to work
try:
    from pymer4.models import Lmer # Lmer handles both lmer and glmer models
except ImportError:
    logging.error("pymer4 not found. Please install it (pip install pymer4)")
    logging.error("Also ensure R is installed and the 'lme4' R package is installed.")
    raise
except Exception as e:
    # Catch potential R interface errors during import
    logging.error(f"Error importing pymer4, potentially R/rpy2 issue: {e}")
    logging.error("Ensure R is installed, in PATH, and 'lme4' R package is installed.")
    raise


# --- Configuration ---
DB_NAME = "rugby"
DB_USER = "clong"  # Replace with your database username
DB_PASSWORD = "psqlnik"  # Replace with your database password
DB_HOST = "localhost"  # Replace with your database host if not local
DB_PORT = "5432"  # Replace with your database port if not default
DB_SCHEMA = "nrl"
DIAGNOSTICS_DIR = "diagnostics"
OUTPUT_LOG_FILE = os.path.join(DIAGNOSTICS_DIR, "glmer_pymer4.log") # Changed log name
MIN_YEAR = 2024
MAX_YEAR = 2025
REFERENCE_YEAR = 2023

# --- Setup Logging ---
os.makedirs(DIAGNOSTICS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(OUTPUT_LOG_FILE, mode='w'),
        logging.StreamHandler()
    ]
)
logging.info("--- Starting Python Script using Pymer4 ---")

# --- Database Connection ---
try:
    db_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = sqlalchemy.create_engine(db_url)
    logging.info(f"Connected to database '{DB_NAME}' on {DB_HOST}:{DB_PORT}")
except Exception as e:
    logging.error(f"Database connection failed: {e}")
    raise

# --- Fetch Data ---
query = f"""
SELECT
    DISTINCT
    r.game_id,
    r.year,
    r.field AS field,
    r.team_name AS team, -- Changed from offense for clarity in Python df
    r.opponent_name AS opponent, -- Changed from defense for clarity
    r.team_score::float AS gs,
    (r.year - {REFERENCE_YEAR}) AS w
FROM {DB_SCHEMA}.results r
WHERE
    r.year BETWEEN {MIN_YEAR} AND {MAX_YEAR}
"""
try:
    logging.info("Fetching data from database...")
    sg = pd.read_sql_query(query, engine)
    logging.info(f"Fetched data shape: {sg.shape}")
    if sg.empty:
        logging.warning("Query returned no data. Exiting.")
        quit()
except Exception as e:
    logging.error(f"Failed to fetch data: {e}")
    engine.dispose()
    raise

# --- Data Preprocessing ---
logging.info("Preprocessing data...")
g = sg.copy()

# --- NEW: Ensure categorical IDs are strings BEFORE converting to category ---
id_cols = ['game_id', 'team', 'opponent'] # Add any other ID-like factors here
for col in id_cols:
    if col in g.columns:
        # Check if the column isn't already stored as strings/objects
        if not pd.api.types.is_string_dtype(g[col]) and not pd.api.types.is_object_dtype(g[col]):
             logging.info(f"Converting column '{col}' to string type before category conversion for R compatibility.")
             g[col] = g[col].astype(str)
        # else: # Optional: log if already string/object
        #     logging.info(f"Column '{col}' is already string/object type.")

# --- Convert relevant columns to categorical type (like R factors) ---
factor_cols = ['field', 'team', 'opponent', 'game_id']
for col in factor_cols:
    if col in g.columns:
        # Now convert to category - categories will be strings if converted above
        g[col] = g[col].astype('category')
        logging.info(f"Converted column '{col}' to category.")
    else:
         logging.warning(f"Column '{col}' not found in fetched data.")

# --- Rest of preprocessing ---
# Ensure 'gs' and 'w' are numeric
g['gs'] = pd.to_numeric(g['gs'])
g['w'] = pd.to_numeric(g['w'])

# Check for NaN/Infinite values (using the corrected check from before)
if not np.isfinite(g[['gs', 'w']].values).all():
    logging.warning("Non-finite values (NaN or +/- Infinity) found in 'gs' or 'w' columns. Check data.")
    # Decide how to handle: drop, impute, or raise error
    # g.dropna(subset=['gs', 'w'], inplace=True) # Example: Drop
else:
    logging.info("Checked 'gs' and 'w' columns: all values are finite.")

# Filter for positive weights (as before)
g_filtered = g[g['w'] > 0].copy()
if len(g_filtered) < len(g):
    logging.warning(f"Removed {len(g) - len(g_filtered)} rows with non-positive weights ('w' column).")
if g_filtered.empty:
    logging.error("No data remaining after filtering for positive weights. Cannot fit model.")
    raise ValueError("No data with positive weights.")

# --- Prepare and Write Parameter Levels ---
# This part remains the same, extracting levels before modeling
logging.info("Extracting parameter levels...")
param_levels_list = []
# Note: R code used 'offense' and 'defense' as parameter names.
# We use 'team' and 'opponent' here based on the SQL query alias.
# Adjust if the database tables expect 'offense'/'defense'.
param_mapping = {'field': 'fixed', 'team': 'random', 'opponent': 'random', 'game_id': 'random'}

for col_name, param_type in param_mapping.items():
    if col_name in g.columns and g[col_name].dtype == 'category':
        levels = g[col_name].cat.categories.tolist()
        df_levels = pd.DataFrame({
            'parameter': col_name, # Use df column name
            'type': param_type,
            'level': levels
        })
        param_levels_list.append(df_levels)

if param_levels_list:
    parameter_levels = pd.concat(param_levels_list, ignore_index=True)
    logging.info(f"Parameter levels DataFrame shape: {parameter_levels.shape}")
    try:
        logging.info("Writing parameter levels to database...")
        parameter_levels.to_sql(
            name='_parameter_levels',
            con=engine,
            schema=DB_SCHEMA,
            if_exists='replace',
            index=False
        )
        logging.info("Successfully wrote parameter levels.")
    except Exception as e:
        logging.error(f"Failed to write parameter levels: {e}")
else:
    logging.warning("No categorical parameter levels found to write.")

# --- Define and Fit Model using Pymer4 ---
logging.info("Defining and fitting the GLMM using Pymer4...")

# Ensure target variable 'gs' is present
if 'gs' not in g.columns:
    logging.error("Target variable 'gs' not found in the data. Cannot fit model.")
    engine.dispose()
    raise ValueError("Target variable 'gs' missing.")

# Define the formula using R-style syntax for pymer4
# Use the column names from the DataFrame 'g' (team, opponent)
model_formula = "gs ~ field + (1|team) + (1|opponent) + (1|game_id)"
logging.info(f"Model formula: {model_formula}")

try:
    # Initialize the Lmer model (handles GLMM via family argument)
    # Note: Ensure the 'w' column doesn't have zeros or negative values if used as weights.
    # Filter out rows with non-positive weights if necessary:
    g_filtered = g[g['w'] > 0].copy()
    if len(g_filtered) < len(g):
        logging.warning(f"Removed {len(g) - len(g_filtered)} rows with non-positive weights ('w' column).")

    if g_filtered.empty:
        logging.error("No data remaining after filtering for positive weights. Cannot fit model.")
        raise ValueError("No data with positive weights.")

    model = Lmer(model_formula, data=g_filtered, family='poisson')

    # Fit the model - pymer4 passes arguments directly to lme4::glmer
    # Check pymer4 docs for exact argument names if 'weights' causes issues
    logging.info("Starting model fit (this may take time)...")
    # Using fit() returns a summary object by default.
    # model.fit(summarize=False) might be needed for direct access if summary() is separate
    # Let's fit and then access attributes:
    model.fit(weights='w', verbose=True) # verbose=True should show R output
    logging.info("Model fitting complete.")

    # --- Log Model Summary ---
    logging.info("--- Model Fit Summary (from Pymer4) ---")
    # Pymer4 model objects usually have a summary attribute or method
    try:
        summary_df = model.summary() # Often returns a DataFrame or list of DataFrames
        if isinstance(summary_df, pd.DataFrame):
             summary_str = summary_df.to_string()
             for line in summary_str.splitlines():
                 logging.info(line)
        elif isinstance(summary_df, list): # Sometimes summary is a list
             for item in summary_df:
                 item_str = str(item)
                 for line in item_str.splitlines():
                      logging.info(line)
        else:
             logging.info(str(summary_df)) # Fallback
    except Exception as summary_e:
        logging.error(f"Could not retrieve or format model summary: {summary_e}")
        logging.info("Attempting to log raw model object instead:")
        logging.info(str(model)) # Log the model object itself for some info

    logging.info("--- End Model Fit Summary ---")

# --- Extract and Format Results ---
    logging.info("Extracting model results (Fixed and Random Effects)...")
    results_list = []
    # Define the random factor names IN THE ORDER THEY APPEAR IN THE FORMULA
    # This is crucial for parsing the model.ranef list correctly
    ranef_factors = ['game_id', 'opponent', 'team']

    # --- Fixed Effects ---
    # Try using model.coefs, as model.fixef was a list previously.
    # model.coefs is typically the DataFrame containing the fixed effects summary table.
    if hasattr(model, 'coefs') and model.coefs is not None:
        coefs_data = model.coefs
        logging.info(f"Attempting to process model.coefs. Type: {type(coefs_data)}")
        if isinstance(coefs_data, pd.DataFrame):
            # Expecting DataFrame with index=level, columns including 'Estimate'
            logging.info("model.coefs is a DataFrame. Extracting estimates.")
            for level, row in coefs_data.iterrows():
                # Use .get() for safer access in case 'Estimate' column is missing/named differently
                estimate = row.get('Estimate', float('nan'))
                if pd.isna(estimate):
                    logging.warning(f"Could not find 'Estimate' column in coefs DataFrame row for level '{level}'. Check DataFrame content logged earlier if summary was printed.")

                # Determine factor name based on level (adapt if more complex)
                factor = 'Intercept' # Default
                if level == '(Intercept)':
                     factor = 'Intercept'
                elif level.startswith('field'): # Check if the level name starts with 'field'
                     factor = 'field'
                # Add more rules here if you have other fixed factors

                results_list.append({
                    'factor': factor,
                    'type': 'fixed',
                    'level': level, # This is the specific level name (e.g., 'Intercept', 'fieldoffense_home')
                    'estimate': estimate
                })
            logging.info(f"Extracted {len(coefs_data)} fixed effect(s) from model.coefs.")
        else:
            # Log if model.coefs is not the expected DataFrame
            logging.warning(f"model.coefs was not a DataFrame (Actual Type: {type(coefs_data)}). Cannot extract fixed effects reliably this way.")
            logging.warning(f"Contents of model.coefs: {str(coefs_data)}")
            # We won't try model.fixef as it was confirmed to be a list of other things
    else:
        # Log if the .coefs attribute doesn't even exist
        logging.warning("Could not find fixed effects attribute 'coefs' on the model object. Unable to extract fixed effects.")
        # Log the problematic fixef attribute again for reference
        if hasattr(model, 'fixef') and model.fixef is not None:
             logging.warning(f"model.fixef (which was problematic) Type: {type(model.fixef)}. Contents: {str(model.fixef)}")


    # --- Random Effects ---
    # Process model.ranef expecting a LIST of DataFrames [game_id_df, opponent_df, team_df]
    if hasattr(model, 'ranef') and model.ranef is not None:
        ranef_data = model.ranef
        logging.info(f"Attempting to process model.ranef. Type: {type(ranef_data)}")

        if isinstance(ranef_data, list):
            # Check if list length matches the number of random factors expected
            if len(ranef_data) == len(ranef_factors):
                logging.info(f"model.ranef is a list with expected length {len(ranef_factors)}. Processing elements.")
                num_ranef_extracted = 0
                # Iterate through the list of DataFrames and the corresponding factor names
                for i, factor_name in enumerate(ranef_factors):
                    df = ranef_data[i]
                    logging.info(f"Processing ranef element {i} for factor '{factor_name}'. Type: {type(df)}")
                    # Check if the element is a DataFrame and has the intercept column
                    if isinstance(df, pd.DataFrame) and '(Intercept)' in df.columns:
                        param_type = 'random'
                        # Iterate through the levels (index) and estimates in this DataFrame
                        for level, row in df.iterrows():
                            estimate = row.get('(Intercept)', float('nan'))
                            if pd.isna(estimate):
                                logging.warning(f"Could not find '(Intercept)' value in ranef DataFrame for factor '{factor_name}', level '{level}'.")

                            results_list.append({
                                'factor': factor_name, # Use the factor name from ranef_factors list
                                'type': param_type,
                                'level': level, # This is the specific level (e.g., game ID, team name)
                                'estimate': estimate
                            })
                            num_ranef_extracted += 1
                        logging.info(f"Extracted {len(df)} levels for random effect '{factor_name}'.")
                    else:
                        # Log if an element in the list is not the expected DataFrame
                        logging.warning(f"Element {i} in model.ranef list (expected for factor '{factor_name}') is not a DataFrame with '(Intercept)' column.")
                        logging.warning(f"Contents of element {i}: {str(df)}")
                logging.info(f"Finished processing ranef list. Total random effect levels extracted: {num_ranef_extracted}")
            else:
                # Log if the list length is wrong
                logging.warning(f"model.ranef is a list, but its length ({len(ranef_data)}) does not match the expected number of random factors ({len(ranef_factors)}). Cannot reliably process.")
                logging.warning(f"Contents of model.ranef list: {str(ranef_data)}")

        # Optional: Keep dict processing code as a fallback? Unlikely needed now.
        # elif isinstance(ranef_data, dict):
        #      logging.info("model.ranef is a dict. Processing as dictionary (less likely path).")
        #      # ... (include previous dict processing code here if desired) ...

        else:
            # Log if model.ranef is neither a list nor a dict
            logging.warning(f"Unexpected type for model.ranef: {type(ranef_data)}. Cannot extract random effects.")
            logging.warning(f"Contents of model.ranef: {str(ranef_data)}")
    else:
         # Log if the .ranef attribute doesn't exist
         logging.warning("Could not find random effects attribute ('ranef') on the model object.")


    # --- Check if results were extracted ---
    if not results_list:
         # Make error more specific based on potential failure points
         logging.error("Failed to extract valid fixed effects (from model.coefs) or random effects (from model.ranef list). Check logs for details on object structures.")
         raise ValueError("Result extraction failed due to unexpected model object attribute structure.")
    else:
         logging.info(f"Successfully extracted {len(results_list)} total factor level estimates into results_list.")


    # --- Write Results to Database ---
    logging.info("Preparing combined DataFrame for database export...")
    combined = pd.DataFrame(results_list)
    logging.info(f"Combined results DataFrame shape: {combined.shape}")
    logging.info("Combined results head:\n" + combined.head().to_string())
    logging.info("Combined results tail:\n" + combined.tail().to_string())

    try:
        logging.info(f"Writing combined results to database table {DB_SCHEMA}._basic_factors...")
        combined.to_sql(
            name='_basic_factors',
            con=engine,
            schema=DB_SCHEMA,
            if_exists='replace',
            index=False
        )
        logging.info("Successfully wrote combined results.")
    except Exception as e:
        logging.error(f"Failed to write combined results: {e}")
        raise # Re-raise exception after logging


    logging.info("Results extraction and writing complete.")

# --- End of try block for model fitting/processing ---
except Exception as e:
    logging.error(f"Model fitting or results processing failed: {e}")
    import traceback
    logging.error(traceback.format_exc())


finally:
    # --- Clean Up ---
    logging.info("Closing database connection.")
    if 'engine' in locals() and engine:
        engine.dispose()
    logging.info("--- Python Script Finished ---")    
