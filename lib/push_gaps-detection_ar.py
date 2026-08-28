import os
import shutil
import tempfile
from dotenv import load_dotenv
from arcgis.gis import GIS, ItemProperties, ItemTypeEnum
import yaml
import geopandas as gpd
import pyogrio

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# load environment variables from .env file
load_dotenv(os.path.join(project_root, ".env"))
with open(os.path.join(project_root, "variables.yaml"), "r", encoding="utf-8") as f:
    variables = yaml.safe_load(f) or {}


gpkg_gaps_path  = variables.get("gapsAR_database")
layers          = pyogrio.list_layers(gpkg_gaps_path)
gapsAR_database = gpd.read_file(gpkg_gaps_path, layer=layers[-1][0])

temp_folder = os.path.join(os.path.dirname(gpkg_gaps_path), "gpa_gaps_detection_planting")
os.makedirs(temp_folder, exist_ok=True)
temp_gapsAR_path = f'{temp_folder}/gpa_gaps_detection_planting.shp'

rename_map = {
    "cls_area_m2":      "cls_m2",
    "cls_area_ha":      "cls_ha",
    "cls_percentage":   "cls_pct",
    "cluster_planting": "clst_plnt",
    "cluster_area_m2":  "clst_m2",
    "cluster_area_ha":  "clst_ha",
}

gapsAR_database_temp = gapsAR_database.rename(columns=rename_map)
gapsAR_database_temp.to_file(temp_gapsAR_path, driver='ESRI Shapefile')

# AGOL requires shapefiles uploaded as a single .zip containing the .shp/.shx/.dbf/.prj siblings
temp_gapsAR_zip = shutil.make_archive(temp_folder, 'zip', temp_folder)

try:
    gis = GIS(
        os.getenv("ARCGIS_PORTAL_URL"),
        os.getenv("ARCGIS_USERNAME"),
        os.getenv("ARCGIS_PASSWORD")
    )
except Exception as e:
    raise RuntimeError(f"Failed to authenticate to ArcGIS Portal: {e}")

title = "gpa_gaps_detection_planting"
folder_name = "farm_intelligence_systems"
target_folder = gis.content.folders.get(folder=folder_name, owner=gis.users.me.username)
if target_folder is None:
    target_folder = gis.content.folders.create(folder=folder_name, owner=gis.users.me.username)

existing = gis.content.search(
    query=f'title:"{title}" AND owner:{gis.users.me.username}',
    item_type="Shapefile"
)

if existing:
    old_item = existing[0]

    # Optional but recommended: warn if anything depends on the hosted layer
    related = old_item.related_items('Service2Data', 'reverse')
    if related:
        print(f"Warning: {len(related)} item(s) reference this layer and will break "
              f"(URL/item ID will change): {[r.title for r in related]}")

    # Also check if a feature layer item with the same title already exists separately
    existing_flayer = gis.content.search(
        query=f'title:"{title}" AND owner:{gis.users.me.username}',
        item_type="Feature Layer"
    )
    for fl in existing_flayer:
        fl.delete(permanent=True)

    old_item.delete(permanent=True)
    print(f"Deleted existing item: {title}")

# Always re-create fresh after delete (or if nothing existed)
item_props = ItemProperties(
    title=title,
    item_type=ItemTypeEnum.SHAPEFILE.value,
    tags=["GPA", "crop establishment", "target", "sugarcane", "paddock"],
    description="Crop Establishment Targets for GPA.",
)

add_job = target_folder.add(
    item_properties=item_props,
    file=temp_gapsAR_zip
)
item = add_job.result()  # resolve the async add operation into an actual Item

feature_layer_item = item.publish(
    publish_parameters={"name": title, "targetSR": {"wkid": 32754}}
)
print(f"Published new layer: {feature_layer_item.url}")
shutil.rmtree(temp_folder)
os.remove(temp_gapsAR_zip)