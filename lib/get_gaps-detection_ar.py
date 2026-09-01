import os
from dotenv import load_dotenv
from arcgis.gis import GIS
import yaml
import geopandas as gpd
import zipfile
from datetime import datetime, timezone, timedelta
import shutil

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── CONFIGURATION ──────────────────────────────────────────────────────────────
# load environment variables from .env file
load_dotenv(os.path.join(project_root, ".env"))

with open(os.path.join(project_root, "data_configuration.yaml"), "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

companies_run   = cfg['companies_run']
c1              = cfg['c1']
c2              = cfg['c2']

def arcgis_get(companies_select):
    print('entering process:', companies_select)
    gpkg_gaps_path        = cfg['companies'][companies_select]['gpkg_gaps_planting_path']

    compLower = companies_select.lower()
    layer_title =  f"{compLower}_gaps_detection_planting"

    
    temp_folder = os.path.join(os.path.dirname(gpkg_gaps_path), layer_title)
    print('temp_folder:', temp_folder)
    os.makedirs(temp_folder, exist_ok=True)

    rename_map = {
        "cls_area_m2":      "cls_m2",
        "cls_area_ha":      "cls_ha",
        "cls_percentage":   "cls_pct",
        "cluster_planting": "clst_plnt",
        "cluster_area_m2":  "clst_m2",
        "cluster_area_ha":  "clst_ha",
    }

    try:
        gis = GIS(
            os.getenv("ARCGIS_PORTAL_URL"),
            os.getenv("ARCGIS_USERNAME"),
            os.getenv("ARCGIS_PASSWORD")
        )
    except Exception as e:
        raise RuntimeError(f"Failed to authenticate to ArcGIS Portal: {e}")
    print(gis)

    folder_name = "farm_intelligence_systems"
    target_folder = gis.content.folders.get(folder=folder_name, owner=gis.users.me.username)
    print('target_folder:', target_folder)
    # if target_folder is None:
    #     target_folder = gis.content.folders.create(folder=folder_name, owner=gis.users.me.username)

    query = f'title:"{layer_title}" AND owner:{gis.users.me.username}'
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


    zip_path = os.path.join(os.path.dirname(gpkg_gaps_path))
    zip_file = selectedLayer.download(save_path=zip_path)
    print(f"Downloaded to: {zip_file}")

    extract_dir = zip_file.replace(".zip", "")
    with zipfile.ZipFile(zip_file, "r") as z:
        z.extractall(extract_dir)

    shp_path = f'{zip_path}/{layer_title}/{layer_title}.shp'

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
    layer_name = f'Gaps-Detection_{company_select}_{modified_date}_Planting_AR'

    print(gapsAR_updateTemp.head())

    gapsAR_updateTemp.to_file(
        gpkg_gaps_path,
        layer=layer_name,
        driver='GPKG'
    )

    # delete all tempfile
    shutil.rmtree(extract_dir)
    os.remove(zip_file)

# Entery Point
if __name__ == "__main__":
   for i in range(len(companies_run)):
       company_select = companies_run[i]
       arcgis_get(companies_select=company_select)
       print(company_select, 'Successfully Processed ......')