import os
from dotenv import load_dotenv
from arcgis.gis import GIS, ItemProperties, ItemTypeEnum
import yaml

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# load environment variables from .env file
load_dotenv(os.path.join(project_root, ".env"))
with open(os.path.join(project_root, "variables.yaml"), "r", encoding="utf-8") as f:
    variables = yaml.safe_load(f) or {}

data_path = variables.get("data_path")
if not data_path:
    raise KeyError("variables.yaml does not contain 'data_path'")

if not os.path.isabs(data_path):
    data_path = os.path.join(project_root, data_path)

if not os.path.exists(data_path):
    raise FileNotFoundError(f"GeoJSON not found at: {data_path}")

try:
    gis = GIS(
        os.getenv("ARCGIS_PORTAL_URL"),
        os.getenv("ARCGIS_USERNAME"),
        os.getenv("ARCGIS_PASSWORD")
    )
except Exception as e:
    raise RuntimeError(f"Failed to authenticate to ArcGIS Portal: {e}")

title = "krebet_sugarcane_farm"
existing = gis.content.search(
    query=f'title:"{title}" AND owner:{gis.users.me.username}',
    item_type="GeoJson"
)

if existing:
    item = existing[0]
    item.update(data=data_path)
    feature_layer_item = item.publish(overwrite=True)
    print(f"Updated existing layer: {feature_layer_item.url}")
else:
    item_props = ItemProperties(
        title=title,
        item_type=ItemTypeEnum.GEOJSON.value,
        tags=["farm", "sugarcane", "paddock"],
        description="Dummy sugarcane farm data around Malang, East Java, Indonesia.",
    )

    add_job  = gis.content.folders.get().add(
        item_properties=item_props,
        file=data_path
    )
    item = add_job.result()  # resolve the async add operation into an actual Item

    feature_layer_item = item.publish()
    print(f"Published new layer: {feature_layer_item.url}")