import os
import tempfile
from dotenv import load_dotenv
from arcgis.gis import GIS, ItemProperties, ItemTypeEnum
import yaml
import geopandas as gpd

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# load environment variables from .env file
load_dotenv(os.path.join(project_root, ".env"))
with open(os.path.join(project_root, "variables.yaml"), "r", encoding="utf-8") as f:
    variables = yaml.safe_load(f) or {}

data_path = variables.get("gpa_crop_establishment_targets")
data_gdf = gpd.read_file(data_path)
if data_gdf.crs != 'EPSG:3857':
    print('Incorrect Refference System, require epsg:3857. Execute reproject layer')
    gdf_3857 = data_gdf.to_crs(epsg=3857)
    data_path = os.path.join(tempfile.mkdtemp(), "gpa_crop_establishment_targets_3857.gpkg")
    gdf_3857.to_file(data_path, driver="GPKG")
    print('Successsfully convert to epsg:3857')

if not data_path:
    raise KeyError("variables.yaml does not contain 'crop_establishment_targets'")

if not os.path.isabs(data_path):
    data_path = os.path.join(project_root, data_path)

if not os.path.exists(data_path):
    raise FileNotFoundError(f"GeoPackage not found at: {data_path}")

try:
    gis = GIS(
        os.getenv("ARCGIS_PORTAL_URL"),
        os.getenv("ARCGIS_USERNAME"),
        os.getenv("ARCGIS_PASSWORD")
    )
except Exception as e:
    raise RuntimeError(f"Failed to authenticate to ArcGIS Portal: {e}")

title = "gpa_crop_establishment_targets"
folder_name = "farm_intelligence_systems"
target_folder = gis.content.folders.get(folder=folder_name, owner=gis.users.me.username)
if target_folder is None:
    target_folder = gis.content.folders.create(folder=folder_name, owner=gis.users.me.username)

existing = gis.content.search(
    query=f'title:"{title}" AND owner:{gis.users.me.username}',
    item_type="GeoPackage"
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
    item_type=ItemTypeEnum.GEOPACKAGE.value,
    tags=["GPA", "crop establishment", "target", "sugarcane", "paddock"],
    description="Crop Establishment Targets for GPA.",
)

add_job = target_folder.add(
    item_properties=item_props,
    file=data_path
)
item = add_job.result()  # resolve the async add operation into an actual Item

feature_layer_item = item.publish()
print(f"Published new layer: {feature_layer_item.url}")