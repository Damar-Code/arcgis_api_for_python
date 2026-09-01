import os
import shutil
import tempfile
from dotenv import load_dotenv
from arcgis.gis import GIS, ItemProperties, ItemTypeEnum
import yaml
import geopandas as gpd
import pyogrio
import argparse
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── CONFIGURATION ──────────────────────────────────────────────────────────────
# load environment variables from .env file
load_dotenv(os.path.join(project_root, ".env"))

with open(os.path.join(project_root, "data_configuration.yaml"), "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

companies_run   = cfg['companies_run']
c1              = cfg['c1']
c2              = cfg['c2']

def arcgis_push(companies_select):
    print('entering process:', companies_select)
    gpkg_gaps_path        = cfg['companies'][companies_select]['gpkg_gaps_planting_path']

    layers          = pyogrio.list_layers(gpkg_gaps_path)
    gapsAR_database = gpd.read_file(gpkg_gaps_path, layer=layers[-1][0])

    compLower = companies_select.lower()
    layer_title =  f"{compLower}_gaps_detection_planting"
    
    temp_folder = os.path.join(os.path.dirname(gpkg_gaps_path), layer_title)
    print('temp_folder:', temp_folder)
    os.makedirs(temp_folder, exist_ok=True)
    temp_gapsAR_path = f'{temp_folder}/{layer_title}.shp'

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

    folder_name = "farm_intelligence_systems"
    target_folder = gis.content.folders.get(folder=folder_name, owner=gis.users.me.username)
    if target_folder is None:
        target_folder = gis.content.folders.create(folder=folder_name, owner=gis.users.me.username)

    existing = gis.content.search(
        query=f'title:"{layer_title}" AND owner:{gis.users.me.username}',
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
            query=f'title:"{layer_title}" AND owner:{gis.users.me.username}',
            item_type="Feature Layer"
        )
        for fl in existing_flayer:
            fl.delete(permanent=True)

        old_item.delete(permanent=True)
        print(f"Deleted existing item: {layer_title}")

    # Always re-create fresh after delete (or if nothing existed)
    item_props = ItemProperties(
        title=layer_title,
        item_type=ItemTypeEnum.SHAPEFILE.value,
        tags=[companies_select, "crop establishment", "target", "sugarcane", "paddock"],
        description= f"Crop Establishment Targets for {companies_select}.",
    )

    add_job = target_folder.add(
        item_properties=item_props,
        file=temp_gapsAR_zip
    )
    item = add_job.result()  # resolve the async add operation into an actual Item

    feature_layer_item = item.publish(
        publish_parameters={"name": layer_title, "targetSR": {"wkid": 32754}}
    )
    print(f"Published new layer: {feature_layer_item.url}")
    shutil.rmtree(temp_folder)
    os.remove(temp_gapsAR_zip)

# Entery Point
if __name__ == "__main__":
   for i in range(len(companies_run)):
       company_select = companies_run[i]
       arcgis_push(companies_select=company_select)
       print(company_select, 'Successfully Processed ......')