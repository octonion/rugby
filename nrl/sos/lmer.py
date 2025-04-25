# -----------------------------------------------------------------------------
# Python Script to Replicate R GLMM Analysis using Pymer4
# -----------------------------------------------------------------------------
# This script fetches rugby data from PostgreSQL, preprocesses it,
# fits a Generalized Linear Mixed-Effects Model (Poisson) using pymer4
# (which wraps R's lme4 package), extracts fixed and random effects,
# and writes the results back to the database.
#
# !! Requires: R installation, lme4 R package, Python packages below !!
# !! May require setting R_LIBS_USER or R_LIBS_SITE environment variable !!
# -----------------------------------------------------------------------------

import pandas as pd
import numpy as np # For checking finite values
import sqlalchemy
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
    logging.error("You might need to set R_LIBS_USER / R_LIBS_SITE environment variables.")
    raise

# --- Import rpy2 for console redirection (Optional but helpful) ---
try:
    import rpy2.robjects as robjects
    import rpy2.rinterface_lib.callbacks
    # Redirect R console output to Python logging
    @rpy2.rinterface_lib.callbacks.consolewrite_print
    def r_print(s):
        logging.info(f"R Console: {s.strip()}")
    @rpy2.rinterface_lib.callbacks.consolewrite_warnerror
    def r_warn(s):
        logging.warning(f"R Message: {s.strip()}") # Capture warnings/errors
    R_OUTPUT_REDIRECTED = True
except ImportError:
    logging.warning("rpy2 not found or console redirection failed. R messages might not be fully captured in log.")
    R_OUTPUT_REDIRECTED = False
except Exception as e:
    logging.warning(f"Error setting up rpy2 console redirection: {e}")
    R_OUTPUT_REDIRECTED = False

# --- Configuration ---
DB_NAME = "rugby"
DB_USER = "clong"  # *** REPLACE with your database username ***
DB_PASSWORD = "psqlnik"  # *** REPLACE with your database password ***
DB_HOST = "localhost"  # Replace with your database host if not local
DB_PORT = "5432"  # Replace with your database port if not default
DB_SCHEMA = "nrl"
DIAGNOSTICS_DIR = "diagnostics"
# Log file name reflects the package used
OUTPUT_LOG_FILE = os.path.join(DIAGNOSTICS_DIR, "glmer_pymer4_final.log")
MIN_YEAR = 2024
MAX_YEAR = 2025
REFERENCE_YEAR = 2023 # Used for calculating 'w'

# --- Setup Logging ---
os.makedirs(DIAGNOSTICS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(OUTPUT_LOG_FILE, mode='w'), # 'w' to overwrite log each run
        logging.StreamHandler() # Also print logs to console
    ]
)
logging.info(f"--- Starting Python Script using Pymer4 ({datetime.now()}) ---")
if R_OUTPUT_REDIRECTED:
    logging.info("R console output will be redirected to this log.")

# --- Database Connection ---
engine = None # Initialize engine to None for finally block
try:
    # Using psycopg2 driver (ensure it's installed: pip install psycopg2 or psycopg2-binary)
    db_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = sqlalchemy.create_engine(db_url)
    # Test connection (optional but recommended)
    with engine.connect() as connection:
        logging.info(f"Successfully connected to database '{DB_NAME}' on {DB_HOST}:{DB_PORT}")

except Exception as e:
    logging.error(f"Database connection failed: {e}")
    # No point continuing if DB connection fails
    raise SystemExit(f"FATAL: Database connection failed - {e}")


# --- Main Processing Block ---
try:
    # --- Fetch Data ---
    query = f"""
    SELECT
        DISTINCT -- Ensure unique rows if source data might have duplicates per game
        r.game_id,
        r.year,
        r.field AS field,
        r.team_name AS team,         -- Aliased for Python DataFrame
        r.opponent_name AS opponent, -- Aliased for Python DataFrame
        r.team_score::float AS gs,   -- Target variable
        (r.year - {REFERENCE_YEAR}) AS w -- Weight column 'w'
    FROM {DB_SCHEMA}.results r
    WHERE
        r.year BETWEEN {MIN_YEAR} AND {MAX_YEAR}
    ORDER BY r.game_id -- Optional: Ensure consistent order if needed downstream
    """
    logging.info("Fetching data from database...")
    sg = pd.read_sql_query(query, engine)
    logging.info(f"Fetched data shape: {sg.shape}")
    if sg.empty:
        logging.warning("Query returned no data. Exiting.")
        # Use SystemExit for clearer exit reason than quit()
        raise SystemExit("No data fetched from database.")

    # --- Data Preprocessing ---
    logging.info("Preprocessing data...")
    g = sg.copy() # Work on a copy

    # --- Convert ID columns to strings BEFORE category conversion ---
    # This avoids the rpy2 warning about converting numeric categories
    id_cols = ['game_id', 'team', 'opponent']
    for col in id_cols:
        if col in g.columns:
            if not pd.api.types.is_string_dtype(g[col]) and not pd.api.types.is_object_dtype(g[col]):
                 logging.info(f"Converting column '{col}' to string type before category conversion for R compatibility.")
                 g[col] = g[col].astype(str)

    # --- Convert relevant columns to categorical type (like R factors) ---
    factor_cols = ['field', 'team', 'opponent', 'game_id']
    for col in factor_cols:
        if col in g.columns:
            g[col] = g[col].astype('category')
            logging.info(f"Converted column '{col}' to category.")
        else:
             logging.warning(f"Factor column '{col}' not found in fetched data.")

    # --- Ensure numeric types for target and weights ---
    g['gs'] = pd.to_numeric(g['gs'])
    g['w'] = pd.to_numeric(g['w'])

    # --- Check for non-finite values in critical columns ---
    if not np.isfinite(g[['gs', 'w']].values).all():
        logging.error("Non-finite values (NaN or +/- Infinity) found in 'gs' or 'w' columns. Cannot proceed.")
        # This is usually a fatal data quality issue for modeling
        raise ValueError("Non-finite values detected in 'gs' or 'w'. Check source data.")
    else:
        logging.info("Checked 'gs' and 'w' columns: all values are finite.")

    # --- Filter out rows with non-positive weights ---
    # lme4 weights typically must be positive
    initial_rows = len(g)
    g_filtered = g[g['w'] > 0].copy()
    rows_filtered = initial_rows - len(g_filtered)
    if rows_filtered > 0:
        logging.warning(f"Removed {rows_filtered} rows with non-positive weights ('w' column <= 0).")
    if g_filtered.empty:
        logging.error("No data remaining after filtering for positive weights. Cannot fit model.")
        raise ValueError("No data with positive weights.")
    logging.info(f"Using {len(g_filtered)} rows for model fitting after weight filtering.")

    # --- Ensure factor_name_map is defined before this section ---
    # (It was defined just before the results extraction in the previous version)
    factor_name_map = {
        'game_id': 'game_id',   # Keep game_id as is
        'opponent': 'defense',  # Map opponent to defense
        'team': 'offense',   # Map team to offense
        'field': 'field'      # Add mapping for field to itself
        # Add mappings for any other parameters if necessary
    }
    logging.info(f"Using factor name map for parameter levels: {factor_name_map}")


    # --- Prepare and Write Parameter Levels ---
    logging.info("Extracting parameter levels...")
    param_levels_list = []
    # Define which internal columns map to fixed/random conceptually for type assignment
    parameter_type_map = {'field': 'fixed', 'team': 'random', 'opponent': 'random', 'game_id': 'random'}

    # Iterate through the internal column names and their types
    for internal_col_name, param_type in parameter_type_map.items():
        # Check if the column exists in the data used for modeling (g_filtered)
        if internal_col_name in g_filtered.columns and pd.api.types.is_categorical_dtype(g_filtered[internal_col_name]):
            # Get the unique levels (categories) from the filtered data
            levels = g_filtered[internal_col_name].cat.categories.tolist()
            if levels: # Proceed only if there are levels
                # --- Apply mapping to get the desired parameter name for the output table ---
                output_parameter_name = factor_name_map.get(internal_col_name, internal_col_name) # Default to internal name if not in map
                if output_parameter_name != internal_col_name:
                    logging.info(f"Mapping internal column '{internal_col_name}' to parameter '{output_parameter_name}' for levels table.")
                # --- End mapping ---

                # Create DataFrame for this parameter's levels
                df_levels = pd.DataFrame({
                    'parameter': output_parameter_name, # Use the mapped name here
                    'type': param_type,                 # Use the type defined in parameter_type_map
                    'level': levels                     # List of unique levels for this parameter
                })
                param_levels_list.append(df_levels)
            else:
                logging.warning(f"No levels found for categorical column '{internal_col_name}' in filtered data.")
        else:
             # Log if column doesn't exist or isn't categorical in the filtered data
             logging.warning(f"Column '{internal_col_name}' not found in filtered data or is not categorical dtype.")


    if param_levels_list:
        parameter_levels = pd.concat(param_levels_list, ignore_index=True)
        # Optional: Sort for consistent output order, matching desired example
        parameter_levels.sort_values(by=['parameter', 'level'], inplace=True)
        logging.info(f"Parameter levels DataFrame shape: {parameter_levels.shape}")
        logging.info("Parameter levels head:\n" + parameter_levels.head().to_string()) # Log head

        try:
            logging.info(f"Writing parameter levels to database table {DB_SCHEMA}._parameter_levels...")
            parameter_levels.to_sql(
                name='_parameter_levels',
                con=engine,
                schema=DB_SCHEMA,
                if_exists='replace', # Overwrite table if it exists
                index=False          # Do not write pandas index
            )
            logging.info("Successfully wrote parameter levels.")
        except Exception as e:
            logging.error(f"Failed to write parameter levels: {e}")
            # Consider if this error should stop the script
            # raise
    else:
        logging.warning("No categorical parameter levels found to write.")

    # --- Define and Fit Model using Pymer4 ---
    # ... (The rest of the script, including model fitting and results extraction, follows) ...

    # --- Define and Fit Model using Pymer4 ---
    logging.info("Defining and fitting the GLMM using Pymer4...")

    # Formula using R-style syntax with DataFrame column names
    model_formula = "gs ~ field + (1|team) + (1|opponent) + (1|game_id)"
    logging.info(f"Model formula: {model_formula}")

    # Initialize the Lmer model
    # Using g_filtered which has positive weights and correct dtypes
    model = Lmer(model_formula, data=g_filtered, family='poisson')

    # Fit the model
    logging.info("Starting model fit (this may take time)...")
    # Pass weights column name; verbose=True shows R output
    model.fit(weights='w', verbose=True, summarize=False) # summarize=False recommended by pymer4 docs
    logging.info("Model fitting complete.")

    # --- Log Model Summary ---
    logging.info("--- Model Fit Summary (from Pymer4) ---")
    try:
        # model.summary() usually provides the formatted summary
        summary_output = model.summary()
        # Summary can be a list or DataFrame, attempt to log nicely
        if isinstance(summary_output, pd.DataFrame):
             summary_str = summary_output.to_string()
             for line in summary_str.splitlines():
                 logging.info(line)
        elif isinstance(summary_output, list):
             for item in summary_output:
                 item_str = str(item)
                 for line in item_str.splitlines():
                      logging.info(line)
        else:
             logging.info(str(summary_output)) # Fallback
    except Exception as summary_e:
        logging.error(f"Could not retrieve or format model summary: {summary_e}")
        logging.info("Attempting to log raw model object attributes for diagnostics:")
        try:
             logging.info(f"Model coefs: {model.coefs}")
             logging.info(f"Model ranef: {model.ranef}")
             logging.info(f"Model loglike: {model.logLike}")
        except:
             logging.info("Could not access basic model attributes.")

    logging.info("--- End Model Fit Summary ---")


    # --- Extract and Format Results ---
    logging.info("Extracting model results (Fixed and Random Effects)...")
    results_list = []
    # Define the random factor names IN THE ORDER THEY APPEAR IN THE FORMULA
    # These are the names based on the DataFrame columns / pymer4 formula
    ranef_factors_internal = ['game_id', 'opponent', 'team']
    # Define mapping from internal names to desired output names for the factor column
    factor_name_map = {
        'game_id': 'game_id',   # game_id maps to itself
        'opponent': 'defense',  # Map 'opponent' factor to 'defense'
        'team': 'offense'   # Map 'team' factor to 'offense'
    }
    logging.info(f"Using factor name map for random effects: {factor_name_map}")

    # --- Fixed Effects ---
    # Try using model.coefs, which should hold the fixed effects summary table
    if hasattr(model, 'coefs') and model.coefs is not None:
        coefs_data = model.coefs
        logging.info(f"Attempting to process model.coefs. Type: {type(coefs_data)}")
        if isinstance(coefs_data, pd.DataFrame):
            logging.info("model.coefs is a DataFrame. Extracting estimates.")
            for level, row in coefs_data.iterrows():
                # Use .get() for safer access, default to NaN if 'Estimate' missing
                estimate = row.get('Estimate', float('nan'))
                if pd.isna(estimate):
                    logging.warning(f"Could not find 'Estimate' column in coefs DataFrame row for level '{level}'.")

                # Set 'factor' column equal to 'level' column for fixed effects per user request
                factor = level

                results_list.append({
                    'factor': factor,  # Use the level name directly
                    'type': 'fixed',
                    'level': level,    # Original level name from index
                    'estimate': estimate
                })
            logging.info(f"Extracted {len(coefs_data)} fixed effect(s) from model.coefs.")
        else:
            logging.warning(f"model.coefs was not a DataFrame (Actual Type: {type(coefs_data)}). Cannot extract fixed effects reliably this way.")
            logging.warning(f"Contents of model.coefs: {str(coefs_data)}")
    else:
        logging.warning("Could not find fixed effects attribute 'coefs' on the model object. Unable to extract fixed effects.")
        # Log the problematic fixef attribute again if it exists, for reference
        if hasattr(model, 'fixef') and model.fixef is not None:
             logging.warning(f"model.fixef (which was problematic) Type: {type(model.fixef)}. Contents: {str(model.fixef)}")


    # --- Random Effects ---
    # Process model.ranef expecting a LIST of DataFrames [game_id_df, opponent_df, team_df]
    if hasattr(model, 'ranef') and model.ranef is not None:
        ranef_data = model.ranef
        logging.info(f"Attempting to process model.ranef. Type: {type(ranef_data)}")

        if isinstance(ranef_data, list):
            # Check if list length matches the number of random factors expected
            if len(ranef_data) == len(ranef_factors_internal):
                logging.info(f"model.ranef is a list with expected length {len(ranef_factors_internal)}. Processing elements.")
                num_ranef_extracted = 0
                # Iterate through the list and the *internal* factor names
                for i, internal_factor_name in enumerate(ranef_factors_internal):
                    df = ranef_data[i]
                    logging.info(f"Processing ranef element {i} for internal factor '{internal_factor_name}'. Type: {type(df)}")
                    # Check if the element is a DataFrame and has the intercept column
                    if isinstance(df, pd.DataFrame) and '(Intercept)' in df.columns:
                        param_type = 'random'
                        # Apply the mapping to get the desired output factor name
                        output_factor_name = factor_name_map.get(internal_factor_name, internal_factor_name) # Use internal name if no map found
                        if output_factor_name != internal_factor_name:
                             logging.info(f"Mapped internal factor '{internal_factor_name}' to output factor '{output_factor_name}'.")

                        # Iterate through the levels (index) and estimates in this DataFrame
                        for level, row in df.iterrows():
                            # Use .get() for safety, default to NaN
                            estimate = row.get('(Intercept)', float('nan'))
                            if pd.isna(estimate):
                                logging.warning(f"Could not find '(Intercept)' value in ranef DataFrame for factor '{internal_factor_name}', level '{level}'.")

                            results_list.append({
                                'factor': output_factor_name, # Use the mapped name for the output table
                                'type': param_type,
                                'level': level, # This is the specific level (e.g., game ID, team name)
                                'estimate': estimate
                            })
                            num_ranef_extracted += 1
                        logging.info(f"Extracted {len(df)} levels for random effect corresponding to '{internal_factor_name}'.")
                    else:
                        # Log if an element in the list is not the expected DataFrame structure
                        logging.warning(f"Element {i} in model.ranef list (expected for factor '{internal_factor_name}') is not a DataFrame with '(Intercept)' column.")
                        logging.warning(f"Contents of element {i}: {str(df)}")
                logging.info(f"Finished processing ranef list. Total random effect levels extracted: {num_ranef_extracted}")
            else:
                # Log if the list length is wrong
                logging.warning(f"model.ranef is a list, but its length ({len(ranef_data)}) does not match the expected number of random factors ({len(ranef_factors_internal)}). Cannot reliably process.")
                logging.warning(f"Contents of model.ranef list: {str(ranef_data)}")
        else:
            # Log if model.ranef is not a list (and also not a dict, handled previously)
            logging.warning(f"Unexpected type for model.ranef: {type(ranef_data)}. Cannot extract random effects.")
            logging.warning(f"Contents of model.ranef: {str(ranef_data)}")
    else:
         # Log if the .ranef attribute doesn't even exist
         logging.warning("Could not find random effects attribute ('ranef') on the model object.")


    # --- Check if any results were successfully extracted ---
    if not results_list:
         # Make error more specific based on potential failure points logged above
         logging.error("Failed to extract valid fixed effects (from model.coefs) or random effects (from model.ranef list). Check logs for details on object structures.")
         raise ValueError("Result extraction failed due to unexpected model object attribute structure.")
    else:
         logging.info(f"Successfully extracted {len(results_list)} total factor level estimates into results_list.")


    # --- Write Combined Results to Database ---
    logging.info("Preparing combined DataFrame for database export...")
    combined = pd.DataFrame(results_list)
    # Optional: Reorder columns to exactly match desired output if needed
    combined = combined[['factor', 'type', 'level', 'estimate']]
    logging.info(f"Combined results DataFrame shape: {combined.shape}")
    # Log head and tail to verify structure before writing
    logging.info("Combined results head:\n" + combined.head().to_string())
    logging.info("Combined results tail:\n" + combined.tail().to_string())

    logging.info(f"Writing combined results to database table {DB_SCHEMA}._basic_factors...")
    combined.to_sql(
        name='_basic_factors',
        con=engine,
        schema=DB_SCHEMA,
        if_exists='replace', # Overwrite table if it exists
        index=False          # Do not write pandas index as a column
    )
    logging.info("Successfully wrote combined results.")
    logging.info("Results extraction and writing complete.")

# --- Global Error Handling & Cleanup ---
except Exception as e:
    # Catch any exceptions not handled within the main block
    logging.error(f"An unexpected error occurred: {e}")
    import traceback
    logging.error(traceback.format_exc()) # Log the full traceback

finally:
    # --- Clean Up ---
    logging.info("Closing database connection if open.")
    if engine: # Check if engine was successfully created
        engine.dispose()
        logging.info("Database connection closed.")
    else:
        logging.info("Database engine was not created.")
    logging.info(f"--- Python Script Finished ({datetime.now()}) ---")

# --- End of script ---

