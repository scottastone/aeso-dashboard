import requests
import json
from flask import Flask, render_template, jsonify

# --- CONFIGURATION ---
# Your AESO API key
api_file = "api.key"

try:
    with open(api_file, "r") as file:
        API_KEY = file.read().strip()
except: 
    API_KEY = ""

if API_KEY == "":
    print("API key not found - did you put it in api.key?")
    exit()

API_URL = "https://apimgw.aeso.ca/public/currentsupplydemand-api/v2/csd/summary/current"
# --- END CONFIGURATION ---

app = Flask(__name__)


def get_processed_aeso_data():
    """
    Fetches data from AESO API and processes it.
    Returns a dictionary with data or an error.
    """
    headers = {"API-KEY": API_KEY}
    try:
        response = requests.get(API_URL, headers=headers)
        response.raise_for_status()
        data = response.json()
        return process_generation_data(data)
    except requests.exceptions.RequestException as e:
        return {"error": f"Error fetching data from API: {e}"}
    except json.JSONDecodeError:
        return {"error": "Error: Failed to parse API response as JSON."}

def process_generation_data(data):
    """
    Parses the generation data from the API response and returns a structured dictionary
    for the web template.
    """
    # Define Categories
    CATEGORY_MAP = {
        "COGENERATION": "Fossil Fuel",
        "COMBINED_CYCLE": "Fossil Fuel",
        "GAS_FIRED_STEAM": "Fossil Fuel",
        "SIMPLE_CYCLE": "Fossil Fuel",
        "WIND": "Renewable",
        "SOLAR": "Renewable",
        "HYDRO": "Renewable",
        "OTHER": "Other",
        "ENERGY_STORAGE": "Other"
    }

    if 'return' not in data:
        return {"error": "Error: 'return' key not found in JSON response."}

    api_return_data = data['return']
    gen_list = api_return_data.get('generation_data_list', [])

    # --- Categorize Data ---
    categorized_data = {
        "Renewable": [],
        "Fossil Fuel": [],
        "Other": []
    }
    
    totals = {
        "mc": {"Renewable": 0.0, "Fossil Fuel": 0.0, "Other": 0.0, "Total": 0.0},
        "tng": {"Renewable": 0.0, "Fossil Fuel": 0.0, "Other": 0.0, "Total": 0.0},
        "dcr": {"Renewable": 0.0, "Fossil Fuel": 0.0, "Other": 0.0, "Total": 0.0}
    }

    for item in gen_list:
        group_name = item.get('fuel_type', 'UNKNOWN').replace(" ", "_").upper()
        category = CATEGORY_MAP.get(group_name, "Other")
        categorized_data[category].append(item)

        try:
            mc = float(item.get('aggregated_maximum_capability', 0))
            tng = float(item.get('aggregated_net_generation', 0))
            dcr = float(item.get('aggregated_dispatched_contingency_reserve', 0))
            
            totals["mc"][category] += mc
            totals["mc"]["Total"] += mc
            totals["tng"][category] += tng
            totals["tng"]["Total"] += tng
            totals["dcr"][category] += dcr
            totals["dcr"]["Total"] += dcr
        except (ValueError, TypeError):
            continue

    # Calculate renewable percentage
    if totals["tng"]["Total"] > 0:
        renewable_percent = (totals["tng"]["Renewable"] / totals["tng"]["Total"]) * 100
    else:
        renewable_percent = 0

    # Calculate fossil fuel percentage
    if totals["tng"]["Total"] > 0:
        fossil_fuel_percent = (totals["tng"]["Fossil Fuel"] / totals["tng"]["Total"]) * 100
    else:
        fossil_fuel_percent = 0

    # Calculate energy storage percentage
    if totals["tng"]["Total"] > 0:
        energy_storage_percent = (totals["tng"]["Other"] / totals["tng"]["Total"]) * 100
    else:
        energy_storage_percent = 0


    # Structure all data for the template
    context = {
        "categories": categorized_data,
        "totals": totals,
        "summary": api_return_data,
        "renewable_percent": renewable_percent,
        "fossil_fuel_percent": fossil_fuel_percent,
        "energy_storage_percent": energy_storage_percent
    }
    return context


@app.route('/')
def index():
    """
    Fetches data and renders the main page.
    """
    try:
        context = get_processed_aeso_data()
    except Exception as e:
        context["error"] = f"An unexpected error occurred: {e}"
    return render_template('index.html', **context)

@app.route('/api/data')
def api_data():
    """
    API endpoint to provide the processed data as JSON.
    """
    data = get_processed_aeso_data()
    return jsonify(data)


if __name__ == '__main__':
    # Use port 2376 as requested
    app.run(debug=True, host='0.0.0.0', port=2376)