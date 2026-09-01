import os

from arcgis.gis import GIS, ItemProperties, ItemTypeEnum
from dotenv import load_dotenv
import yaml
import geopandas as gpd
import pyogrio

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── CONFIGURATION ──────────────────────────────────────────────────────────────
# load environment variables from .env file
load_dotenv(os.path.join(project_root, ".env"))

with open(os.path.join(project_root, "data_configuration.yaml"), "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

companies_run   = cfg['companies_run']
c1              = cfg['c1']
c2              = cfg['c2']

try:
    credential = GIS(
        os.getenv("ARCGIS_PORTAL_URL"),
        os.getenv("ARCGIS_USERNAME"),
        os.getenv("ARCGIS_PASSWORD")
    )
except Exception as e:
    raise RuntimeError(f"Failed to authenticate to ArcGIS Portal: {e}")

def arcgisPush_sugarcaneGeneric(companies_select, gis):
    print('entering process:', companies_select)
    sugarcane_gdb_path      = cfg['companies'][companies_select]['sugarcane_gdb_path']
    layers                  = pyogrio.list_layers(sugarcane_gdb_path)
    sugarcane_database      = gpd.read_file(sugarcane_gdb_path, layer=layers[-1][0])

    comp_lower = companies_select.lower()
    layer_title =  f"{comp_lower}_sugarcane_generic"

    temp_folder = os.path.join(os.path.dirname(sugarcane_gdb_path))
    print('temp_folder:', temp_folder)
    os.makedirs(temp_folder, exist_ok=True)
    temp_sugarcane_generic_path = f'{temp_folder}/{layer_title}.parquet'
    print('temp_sugarcane_path:', temp_sugarcane_generic_path)

    sugarcane_generic = sugarcane_database.copy()
    sugarcane_generic["x"] = round(sugarcane_generic.geometry.x, 3)
    sugarcane_generic["y"] = round(sugarcane_generic.geometry.y, 3)
    sugarcane_generic = sugarcane_generic[["x","y"]]  # now a plain pandas DataFrame, no WKB overhead
    sugarcane_generic.to_parquet(temp_sugarcane_generic_path, 
                                 index=False, 
                                 compression="gzip") # smaller

    folder_name = "farm_intelligence_systems"
    target_folder = gis.content.folders.get(folder=folder_name, owner=gis.users.me.username)
    if target_folder is None:
        target_folder = gis.content.folders.create(folder=folder_name, owner=gis.users.me.username)

    existing = gis.content.search(
        query=f'title:"{layer_title}" AND owner:{gis.users.me.username}',
        item_type="Apache Parquet"
    )

    if existing:
        for item in existing:
            print(f"Found existing item: {item.title} ({item.type}) - {item.id}")
            item.delete(permanent=True)
            print(f"Deleted: {item.title}")
    else:
        print(f"No existing item found with title '{layer_title}' - nothing to delete.")
    
    item_props = ItemProperties(
        title= layer_title,
        item_type= ItemTypeEnum.APACHE_PARQUET.value,
        tags= [comp_lower, "archive", "sugarcane", "points", "parquet", "raw"],
        description= "Non-spatial raw sugarcane point positions (x, y in EPSG:32754). Reconstruct locally with gpd.points_from_xy().",
    )

    add_job = target_folder.add(
        item_properties=item_props,
        file=temp_sugarcane_generic_path,  # upload the raw .parquet directly, no zip needed
    )
    archive_item = add_job.result()
    print(f"Successfully uploaded: {archive_item.title} (ID: {archive_item.id})")

    # remove temporary file
    os.remove(temp_sugarcane_generic_path)

# Entery Point
if __name__ == "__main__":
   for i in range(len(companies_run)):
       company_select = companies_run[i]
       arcgisPush_sugarcaneGeneric(companies_select=company_select, gis=credential)
       