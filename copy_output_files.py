import sys
import pathlib
import os
import shutil

# Paths of results files and .filter_id file
results_gdx_path = pathlib.Path(sys.argv[1])
debug_invest_gdx_path = pathlib.Path(sys.argv[2])
filter_id_path = results_gdx_path.parent.parent.parent / ".filter_id"

# Read scenario info from .filter_id file
with open(filter_id_path, encoding="utf-8") as filter_id_file:
        filter_id = filter_id_file.readline().strip()

# Parse scenario name 
front = filter_id[: -len(" - BB_sets")]
filter_1_name, filter_2_name = (name.strip() for name in front.split(","))
scenario = filter_1_name if filter_1_name != "& Backbone" else filter_2_name

# Path for the results folder in project root
results_path = filter_id_path.parent.parent.parent.parent.parent.parent / "Results"
scenario_results_path = results_path / scenario

# Create the results folder if it doesn't exist
if not os.path.exists(scenario_results_path):
  os.mkdir(scenario_results_path)

# Copy scenario results to the destination folder
shutil.copy(results_gdx_path, scenario_results_path / "results.gdx")
shutil.copy(debug_invest_gdx_path, scenario_results_path / "debug-invest.gdx")
