import os
import shutil
import tempfile
from dotenv import load_dotenv
from arcgis.gis import GIS, ItemProperties, ItemTypeEnum
import yaml
import geopandas as gpd
import pyogrio
from arcgis.features import FeatureLayer
import zipfile
from datetime import datetime, timezone, timedelta

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# load environment variables from .env file
load_dotenv(os.path.join(project_root, ".env"))
with open(os.path.join(project_root, "data_configuration.yaml"), "r", encoding="utf-8") as f:
    variables = yaml.safe_load(f) or {}

app_root        = variables.get("app_root")
gpkg_gaps_path  = variables.get("gapsAR_database")
# layers          = pyogrio.list_layers(gpkg_gaps_path)
# gapsAR_database = gpd.read_file(gpkg_gaps_path, layer=layers[-1][0])

# temp_folder = os.path.join(os.path.dirname(gpkg_gaps_path), "gpa_gaps_detection_planting")
# os.makedirs(temp_folder, exist_ok=True)
# temp_gapsAR_path = f'{temp_folder}/gpa_gaps_detection_planting.shp'

rename_map = {
    "cls_area_m2":      "cls_m2",
    "cls_area_ha":      "cls_ha",
    "cls_percentage":   "cls_pct",
    "cluster_planting": "clst_plnt",
    "cluster_area_m2":  "clst_m2",
    "cluster_area_ha":  "clst_ha",
}

# gapsAR_database_temp = gapsAR_database.rename(columns=rename_map)
# gapsAR_database_temp.to_file(temp_gapsAR_path, driver='ESRI Shapefile')

# AGOL requires shapefiles uploaded as a single .zip containing the .shp/.shx/.dbf/.prj siblings
# temp_gapsAR_zip = shutil.make_archive(temp_folder, 'zip', temp_folder)

try:
    gis = GIS(
        os.getenv("ARCGIS_PORTAL_URL"),
        os.getenv("ARCGIS_USERNAME"),
        os.getenv("ARCGIS_PASSWORD")
    )
except Exception as e:
    raise RuntimeError(f"Failed to authenticate to ArcGIS Portal: {e}")
print(gis)

title = "gpa_gaps_detection_planting"
folder_name = "farm_intelligence_systems"
target_folder = gis.content.folders.get(folder=folder_name, owner=gis.users.me.username)
print('target_folder:', target_folder)
# if target_folder is None:
#     target_folder = gis.content.folders.create(folder=folder_name, owner=gis.users.me.username)

query = f'title:"{title}" AND owner:{gis.users.me.username}'
selectedLayer = gis.content.search(query=query, item_type="Shapefile")[0]
print('selectedLayer:', selectedLayer)

# print(vars(selectedLayer)) ### READ ALL AVAILABLE VARIABLES

def item_timestamps(item, tz_offset_hours: int = 7) -> dict:
    """Convert an Item's created/modified epoch-ms fields to readable
    local time (default: Jakarta, UTC+7)."""
    tz = timezone(timedelta(hours=tz_offset_hours))
    return {
        "created": datetime.fromtimestamp(item.created / 1000, tz=tz),
        "modified": datetime.fromtimestamp(item.modified / 1000, tz=tz),
    }
layerMetaDataSelected = item_timestamps(selectedLayer)
print('layerMetaDataSelected: ', layerMetaDataSelected)

zip_path = f'{app_root}/database/GPA/'
zip_file = selectedLayer.download(save_path=zip_path)
print(f"Downloaded to: {zip_file}")

extract_dir = zip_file.replace(".zip", "")
with zipfile.ZipFile(zip_file, "r") as z:
    z.extractall(extract_dir)

shp_path = f'{zip_path}{title}/{title}.shp'
gapsAR_update = gpd.read_file(shp_path)
rename_map = {
    "cls_m2":    "cls_area_m2",
    "cls_ha":    "cls_area_ha",
    "cls_pct":   "cls_percentage",
    "clst_plnt": "cluster_planting",
    "clst_m2":   "cluster_area_m2",
    "clst_ha":   "cluster_area_ha",
}

gapsAR_updateTemp = gapsAR_update.rename(columns=rename_map)
modified_date = layerMetaDataSelected["modified"].strftime("%Y%m%d")
layer_name = f'Gaps-Detection_GPA_{modified_date}_Planting_AR'

print(gapsAR_updateTemp.head())

gapsAR_updateTemp.to_file(
    gpkg_gaps_path,
    layer=layer_name,
    driver='GPKG'
)