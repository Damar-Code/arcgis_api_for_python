from arcgis.gis import GIS
from dotenv import load_dotenv
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── CONFIGURATION ──────────────────────────────────────────────────────────────
# load environment variables from .env file
load_dotenv(os.path.join(project_root, ".env"))

# Connect to your ArcGIS Enterprise Portal
gis = GIS(
        os.getenv("ARCGIS_PORTAL_URL"),
        os.getenv("ARCGIS_USERNAME"),
        os.getenv("ARCGIS_PASSWORD")
    )

# Define item metadata
item_properties = {
    "title": "Project Archive Files",
    "type": "Zip",  # Explicitly sets it as a generic zip file item
    "tags": "archive, backup, documents",
    "description": "Non-spatial generic archive containing project assets."
}

# Upload the file directly without calling the .publish() method
archive_item = gis.content.add(
    item_properties=item_properties,
    data=r"C:\path\to\your\archive.zip"
)

print(f"Successfully uploaded: {archive_item.title} (ID: {archive_item.id})")
