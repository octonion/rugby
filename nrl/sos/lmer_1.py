import pandas as pd
import sqlalchemy
import statsmodels.formula.api as smf
import statsmodels.api as sm
import logging
import os
from datetime import datetime

# --- Configuration ---
DB_NAME = "rugby"
DB_USER = "clong"  # Replace with your database username
DB_PASSWORD = "psqlnik"  # Replace with your database password
DB_HOST = "localhost"  # Replace with your database host if not local
DB_PORT = "5432"  # Replace with your database port if not default
DB_SCHEMA = "nrl"
DIAGNOSTICS_DIR = "diagnostics"
OUTPUT_LOG_FILE = os.path.join(DIAGNOSTICS_DIR, "lmer_python.log")
MIN_YEAR = 2024
MAX_YEAR = 2025
REFERENCE_YEAR = 2023

# --- Setup Logging ---
# Ensure diagnostics directory exists
os.makedirs(DIAGNOSTICS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(OUTPUT_LOG_FILE, mode='w'), # 'w' to overwrite like sink
        logging.StreamHandler() # Also print to console
    ]
)
logging.info("--- Starting Python Script ---")

# --- Database Connection ---
try:
    # Using psycopg2 driver
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
    r.team_name AS team,
    r.opponent_name AS opponent,
    r.team_score::float AS gs,
    (r.year - {REFERENCE_YEAR}) AS w -- Calculate weight column 'w'
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
        quit() # Or sys.exit()

except Exception as e:
    logging.error(f"Failed to fetch data: {e}")
    engine.dispose()
    raise

# --- Data Preprocessing ---
logging.info("Preprocessing data...")

# R code replicates rows based on 'w'. We'll use 'w' as frequency weights instead.
# games = sg.loc[sg.index.repeat(sg['w'])].reset_index(drop=True) # Uncomment if row replication is truly needed
# logging.info(f"Data shape after potential row replication: {games.shape}")
# Instead, we use the original 'sg' DataFrame and pass 'w' as weights later.
g = sg.copy() # Create a copy to work with

# Convert relevant columns to categorical type (like R factors)
# Fixed effects in the model formula
fixed_factors = ['field']
# Factors treated as random effects in R, but as fixed effects in this Python GLM translation
random_factors_as_fixed = ['team', 'opponent', 'game_id']

for col in fixed_factors + random_factors_as_fixed:
    if col in g.columns:
        g[col] = g[col].astype('category')
        logging.info(f"Converted column '{col}' to category. Levels: {g[col].cat.categories.tolist()}")
    else:
         logging.warning(f"Column '{col}' not found in fetched data.")

# Ensure 'gs' and 'w' are numeric
g['gs'] = pd.to_numeric(g['gs'])
g['w'] = pd.to_numeric(g['w'])

# --- Prepare and Write Parameter Levels ---
logging.info("Extracting parameter levels...")
param_levels_list = []

# R 'fp' equivalent columns
for col_name in fixed_factors:
    if col_name in g.columns and g[col_name].dtype == 'category':
        levels = g[col_name].cat.categories.tolist()
        df_levels = pd.DataFrame({
            'parameter': col_name,
            'type': 'fixed',
            'level': levels
        })
        param_levels_list.append(df_levels)

# R 'rp' equivalent columns (treated as fixed here)
for col_name in random_factors_as_fixed:
     if col_name in g.columns and g[col_name].dtype == 'category':
        levels = g[col_name].cat.categories.tolist()
        df_levels = pd.DataFrame({
            'parameter': col_name,
            # NOTE: R code called these 'random', but our GLM treats them as 'fixed'
            'type': 'fixed_effect_approximation', # Be explicit about the difference
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
            if_exists='replace', # Choose 'fail', 'replace', or 'append'
            index=False # R's dbWriteTable default is often row.names=FALSE
        )
        logging.info("Successfully wrote parameter levels.")
    except Exception as e:
        logging.error(f"Failed to write parameter levels: {e}")
else:
    logging.warning("No categorical parameter levels found to write.")


# --- Define and Fit Model ---
# NOTE: Translating R's glmer(gs ~ field + (1|offense) + (1|defense) + (1|game_id), family=poisson)
#       to Python's statsmodels. This uses GLM with fixed effects for all factors,
#       as statsmodels doesn't have a direct frequentist Poisson GLMM equivalent.
#       The 'team' column corresponds to R's 'offense', 'opponent' to R's 'defense'.
logging.info("Defining and fitting the model...")
logging.warning("NOTE: Translating R GLMM to Python GLM (fixed effects only).")

# Ensure target variable 'gs' is present
if 'gs' not in g.columns:
    logging.error("Target variable 'gs' not found in the data. Cannot fit model.")
    engine.dispose()
    raise ValueError("Target variable 'gs' missing.")

# Define the formula using Patsy syntax (used by statsmodels.formula.api)
# C() indicates categorical treatment for factors
model_formula = "gs ~ C(field) + C(team) + C(opponent) + C(game_id)"
logging.info(f"Model formula: {model_formula}")

try:
    # Use Poisson GLM with log link
    # Use 'w' column as frequency weights (interpreting R's row replication/weights)
    poisson_model = smf.glm(
        formula=model_formula,
        data=g,
        family=sm.families.Poisson(link=sm.families.links.log()),
        freq_weights=g['w'] # Use 'freq_weights' if w represents observation counts
        # Alternatively use var_weights=g['w'] if w represents variance weights
    )
    fit = poisson_model.fit()
    logging.info("Model fitting complete.")

    # --- Log Model Summary ---
    logging.info("--- Model Fit Summary ---")
    # Convert summary to string to log it properly
    summary_str = str(fit.summary())
    # Log line by line to avoid potential formatting issues in log file
    for line in summary_str.splitlines():
        logging.info(line)
    logging.info("--- End Model Fit Summary ---")


    # --- Extract and Format Results ---
    logging.info("Extracting model results...")
    results_list = []

    # Get coefficients (all are treated as fixed effects in this GLM)
    params = fit.params

    for level, estimate in params.items():
        factor = 'Intercept' # Default
        param_type = 'fixed' # All effects are fixed in this GLM

        if level == 'Intercept':
            factor = 'Intercept'
        elif level.startswith('C(field)['):
             factor = 'field'
        elif level.startswith('C(team)['):
             factor = 'team' # R code used 'offense'
        elif level.startswith('C(opponent)['):
             factor = 'opponent' # R code used 'defense'
        elif level.startswith('C(game_id)['):
             factor = 'game_id'
        # Add more elif blocks if other factors are included

        results_list.append({
            'factor': factor,
            'type': param_type,
            'level': level, # The full level name from statsmodels summary
            'estimate': estimate
        })

    combined = pd.DataFrame(results_list)
    logging.info(f"Combined results DataFrame shape: {combined.shape}")

    # --- Write Results to Database ---
    try:
        logging.info("Writing combined results (_basic_factors) to database...")
        combined.to_sql(
            name='_basic_factors',
            con=engine,
            schema=DB_SCHEMA,
            if_exists='replace',
            index=False # R script used row.names=TRUE, check if index needed
                       # If index needed, change to index=True and maybe name index
        )
        logging.info("Successfully wrote combined results.")
    except Exception as e:
        logging.error(f"Failed to write combined results: {e}")

except Exception as e:
    logging.error(f"Model fitting or results processing failed: {e}")
    # Potentially log more details or partial results if needed

finally:
    # --- Clean Up ---
    logging.info("Closing database connection.")
    if 'engine' in locals() and engine:
        engine.dispose()
    logging.info("--- Python Script Finished ---")

# End of script (equivalent to R's quit("no"))
