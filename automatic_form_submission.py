# =============================================================================
# DATA CENTRE MAPPING — Automated Form Submission Script
# =============================================================================
#
# INSTRUCTIONS FOR STUDENTS
# --------------------------
# 1. Install dependencies:
#       pip install requests pandas
#
# 2. Place this script in the same folder as your .tsv data file. 
# If your file is formatted differently than tab-separated values, change the way the file is read
#
# 3. Set CSV_FILE (below) to the name of your .tsv file.
#
# 4. Run with SEND = False first to validate your data.
#    You will see a full report of errors WITHOUT submitting anything.
#
# 5. Fix any errors in your .tsv file, then run again with SEND = True.
#
# =============================================================================
# !! CRITICAL WARNING — READ BEFORE RUNNING WITH SEND = True !!
# =============================================================================
#
# **DO NOT RUN THIS SCRIPT MORE THAN ONCE ON THE SAME DATASET.**
# **Every execution with SEND = True submits ALL valid rows to the form.**
# **Duplicate submissions pollute the shared database and must be removed**
# **manually by the course staff. Run it ONCE, and ONLY ONCE.**
#
# =============================================================================
# DO NOT MODIFY THE VALIDATION SECTION (clearly marked below).
# The checks replicate EXACTLY the constraints defined in the Google Form.
# Removing or weakening them will allow invalid data into the shared database.
# =============================================================================

import re
import time
import requests
import pandas as pd

# =============================================================================
# CONFIGURATION — only edit this section
# =============================================================================

CSV_FILE = "your_csv_file.tsv"  # your .tsv file 
                                # If you are using another file extension change the import accordingly
SEND     = False   # set to True ONLY when you are ready to submit for real
DELAY    = 2.0     # seconds between submissions — do not lower this value

# =============================================================================
# FORM ENDPOINTS  (do not change)
# =============================================================================

FORM_ID  = "formID" #INSERT FORM ID
FORM_URL = f"https://docs.google.com/forms/d/e/{FORM_ID}/viewform"
POST_URL = f"https://docs.google.com/forms/d/e/{FORM_ID}/formResponse"

# =============================================================================
# FIELD MAP  —  entry ID  ->  column name in the .tsv
#
# The entry IDs on the LEFT must not be changed.
# Adjust the column names on the RIGHT only if your .tsv headers differ.
# =============================================================================

ENTRY_MAP = {
    "entry.320628032":  "Group Number ID",
    "entry.486861776":  "Unique Data Centre ID",
    "entry.1972904144": "Data Centre Name",
    "entry.908908597":  "Operator",
    "entry.673944872":  "Street Address",
    "entry.850496348":  "City",
    "entry.542465020":  "Postal Code / ZIP Code",
    "entry.1365808410": "Country ISO2 code",
    "entry.963378994":  "Coordinates (Latitude, Longitude)",
    "entry.1346551664": "NUTS3 Region Code",
    "entry.1125580182": "Primary Source Confirming the Data Centre",
    "entry.1771583486": "News Articles Mentioning the Data Centre",
    "entry.1614300136": "Individuals Mentioned in News",
    "entry.1842784360": "Operating Company (Legal Entity / Permit Applicant)",
    "entry.410056195":  "Parent Company",
    "entry.2061530222": "Is the operator or its parent company backed or owned by a private equity fund or asset manager?",
    "entry.1341620919": "Source for Ownership Information (URL)",
    "entry.360157987":  "Construction Year",
    "entry.1476933402": "Estimated IT Load (MW)",
    "entry.1163342674": "Generator Type",
    "entry.399398013":  "Total Generator Rated Capacity (MW)",
    "entry.985202037":  "Annual Water Consumption",
    "entry.425180581":  "Water Source (Basin / Aquifer)",
    "entry.409780800":  "CO2e Emissions (tons per year)",
    "entry.539905950":  "Information Source(s)",
}

# =============================================================================
# !! DO NOT MODIFY ANYTHING BELOW THIS LINE !!
# VALIDATION RULES — exact replica of the Google Form constraints
# =============================================================================

# Regex patterns copied verbatim from the form HTML source
RE_ISO2 = re.compile(
    r"^(BE|BG|CZ|DK|DE|EE|IE|EL|ES|FR|HR|IT|CY|LV|LT|LU|HU|MT|NL|AT|PL|PT"
    r"|RO|SI|SK|FI|SE|IS|LI|NO|CH|ME|MK|AL|RS|TR|UA|XK)$"
)
RE_COORDS = re.compile(
    r"^-?([1-8]?\d(\.\d+)?|90(\.0+)?),\s-?((1[0-7]\d)|([1-9]?\d)|180)(\.\d+)?$"
)

# Allowed values for radio button fields (from form JSON)
VALID_PE_VALUES = {"Yes", "No", "Unknown"}
VALID_GEN_VALUES = {
    "Diesel",
    "Natural Gas",
    "HVO (Hydrotreated Vegetable Oil)",
    "Biogas",
    "Dual-fuel (Diesel + Gas)",
    "Battery-only backup",
    "Hydrogen",
    "Unknown",
}

# Mandatory fields — required=1 in the form JSON
REQUIRED_FIELDS = [
    "Group Number ID",
    "Unique Data Centre ID",
    "Data Centre Name",
    "Operator",
    "Street Address",
    "City",
    "Postal Code / ZIP Code",
    "Country ISO2 code",
    "Coordinates (Latitude, Longitude)",
    "NUTS3 Region Code",
    "Primary Source Confirming the Data Centre",
    "News Articles Mentioning the Data Centre",
    "Individuals Mentioned in News",
]


def validate_row(row):
    """
    Replicates all validation rules from the Google Form.
    Returns a list of error messages. Empty list means the row is valid.
    """
    errors = []

    # 1. Mandatory fields must not be empty
    for field in REQUIRED_FIELDS:
        if str(row.get(field, "")).strip() == "":
            errors.append(f"[REQUIRED] Empty mandatory field: '{field}'")

    # 2. Group Number ID — max 10 characters (maxLength constraint from form)
    group_id = str(row.get("Group Number ID", "")).strip()
    if len(group_id) > 10:
        errors.append(
            f"[FORMAT] 'Group Number ID' is too long "
            f"({len(group_id)} chars, max 10): '{group_id}'"
        )

    # 3. Country ISO2 code — exact regex from the form source
    iso2 = str(row.get("Country ISO2 code", "")).strip()
    if iso2 and not RE_ISO2.match(iso2):
        errors.append(
            f"[FORMAT] Invalid 'Country ISO2 code': '{iso2}'\n"
            f"         Allowed: BE BG CZ DK DE EE IE EL ES FR HR IT CY LV LT LU\n"
            f"         HU MT NL AT PL PT RO SI SK FI SE IS LI NO CH ME MK AL RS TR UA XK"
        )

    # 4. Coordinates — exact regex from the form source
    coords = str(row.get("Coordinates (Latitude, Longitude)", "")).strip()
    if coords and not RE_COORDS.match(coords):
        errors.append(
            f"[FORMAT] Invalid 'Coordinates': '{coords}'\n"
            f"         Use Google Maps format: 45.4642, 9.1900  (lat, space, lon)"
        )

    # 5. PE question — only allowed radio values
    pe_col = (
        "Is the operator or its parent company backed or owned by a "
        "private equity fund or asset manager?"
    )
    pe = str(row.get(pe_col, "")).strip()
    if pe and pe not in VALID_PE_VALUES:
        errors.append(
            f"[FORMAT] Invalid PE answer: '{pe}'\n"
            f"         Allowed values: Yes / No / Unknown"
        )

    # 6. Generator Type — only allowed radio values
    gen = str(row.get("Generator Type", "")).strip()
    if gen and gen not in VALID_GEN_VALUES:
        errors.append(
            f"[FORMAT] Invalid 'Generator Type': '{gen}'\n"
            f"         Allowed: {' / '.join(sorted(VALID_GEN_VALUES))}"
        )

    return errors


def get_fbzx():
    """
    Fetches the fbzx session token dynamically from the live form page.
    This value is regenerated by Google on every page load and must be
    read fresh — using a hardcoded value will cause submissions to fail.
    """
    try:
        r = requests.get(FORM_URL, timeout=10)
        match = re.search(r'name="fbzx" value="(-?\d+)"', r.text)
        if match:
            return match.group(1)
        # fallback: try data-shuffle-seed attribute
        match = re.search(r'data-shuffle-seed="(-?\d+)"', r.text)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"  WARNING: could not fetch fbzx dynamically ({e}). Using fallback.")
    return "-9151365495411357258"  # last known value from form source


# =============================================================================
# LOAD DATA
# =============================================================================

df = pd.read_csv(CSV_FILE, sep="\t").fillna("")

# Rename email column if exported from a Google Form in Italian
if "Indirizzo email" in df.columns and "Email" not in df.columns:
    df.rename(columns={"Indirizzo email": "Email"}, inplace=True)

print(f"Columns found in the .tsv:\n  {list(df.columns)}\n")
print(f"Total rows to process: {len(df)}")
print("=" * 65)

# =============================================================================
# MAIN LOOP
# =============================================================================

ok_count     = 0
failed_valid = []   # rows skipped due to validation errors
failed_send  = []   # rows where the HTTP request failed

# Fetch the fbzx token once before the loop
fbzx = get_fbzx()
print(f"fbzx session token: {fbzx}\n")

for i, row in df.iterrows():
    print(f"\nRow {i+1}/{len(df)} — {str(row.get('Data Centre Name', '???'))[:55]}")

    # --- Validate ---
    errors = validate_row(row)
    if errors:
        print(f"  x SKIPPED — {len(errors)} validation error(s):")
        for e in errors:
            for line in e.split("\n"):
                print(f"    {line}")
        failed_valid.append(i + 1)
        continue

    print("  v Validation passed")

    # --- Build POST payload ---
    payload = {
        "emailAddress":        str(row.get("Email", "")).strip(),
        "fvv":                 "1",
        "pageHistory":         "0,1,2,3",
        "fbzx":                fbzx,
        "submissionTimestamp": "-1",
    }
    for entry_id, col_name in ENTRY_MAP.items():
        if col_name in df.columns:
            val = str(row[col_name]).strip()
            if val:
                payload[entry_id] = val

    # --- Submit or dry-run ---
    if SEND:
        try:
            r = requests.post(
                POST_URL, data=payload, allow_redirects=False, timeout=15
            )
            if r.status_code in (200, 302):
                print("  -> Submitted successfully")
                ok_count += 1
            else:
                print(f"  -> WARNING: unexpected HTTP status {r.status_code}")
                failed_send.append(i + 1)
        except Exception as e:
            print(f"  -> CONNECTION ERROR: {e}")
            failed_send.append(i + 1)
        time.sleep(DELAY)
    else:
        fields = [k for k in payload if k.startswith("entry")]
        print(f"  -> TEST MODE — {len(fields)} fields ready to send")

# =============================================================================
# SUMMARY
# =============================================================================

print("\n" + "=" * 65)
print("FINAL SUMMARY")
print(f"  Total rows in file:          {len(df)}")
print(f"  Skipped (validation errors): {len(failed_valid)}")
print(f"  Failed (HTTP errors):        {len(failed_send)}")
if SEND:
    print(f"  Successfully submitted:      {ok_count}")
else:
    print("  (SEND = False — nothing was actually submitted)")

if failed_valid:
    print(f"\n  Rows with validation errors: {failed_valid}")
if failed_send:
    print(f"  Rows with HTTP errors:       {failed_send}")
