import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OAMHarvester:
    """
    Search and retrieve high-resolution drone and satellite imagery 
    from the OpenAerialMap (OAM) Open Imagery Network.
    """
    API_URL = "https://api.openaerialmap.org/meta"

    def search_imagery(self, lat, lon, buffer=0.01):
        """
        Search for images covering a coordinate.
        OAM uses BBOX: xmin, ymin, xmax, ymax
        """
        xmin = lon - buffer
        ymin = lat - buffer
        xmax = lon + buffer
        ymax = lat + buffer
        
        url = f"{self.API_URL}?bbox={xmin},{ymin},{xmax},{ymax}"
        
        try:
            response = requests.get(url, timeout=35, headers={"User-Agent": "RoofHunter-OAM/1.0"})
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                logger.info(f"OAM: Found {len(results)} high-res scenes for coordinate ({lat}, {lon})")
                return results
            else:
                logger.error(f"OAM API Error: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"OAM Request Failed: {e}")
            return []

    def _scene_download_url(self, scene: dict) -> tuple[str | None, str | None]:
        """
        Prefer a small PNG thumbnail for vision pipelines; GeoTIFF is in scene['uuid']
        when the API exposes an https URL there.
        """
        props = scene.get("properties") or {}
        thumb = props.get("thumbnail")
        if isinstance(thumb, str) and thumb.startswith("http"):
            return thumb, "thumbnail"
        u = scene.get("uuid")
        if isinstance(u, str) and u.startswith("http"):
            lowered = u.lower()
            if lowered.endswith(".png") or lowered.endswith(".jpg") or lowered.endswith(".jpeg"):
                return u, "raster_preview"
            return None, None
        return None, None

    def get_best_image(self, lat, lon, buffer=0.01):
        """
        Returns metadata plus an HTTP URL suitable for downloads (PNG/JPEG thumbnail
        when available), highest resolution first (lower gsd).

        Compatibility: ``url`` is the thumbnail or preview URL callers should GET;
        GeoTIFF links are intentionally skipped here (often huge files).
        """
        scenes = self.search_imagery(lat, lon, buffer=buffer)
        if not scenes:
            return None

        def _gd(scene: dict) -> float:
            g = scene.get("gsd")
            try:
                return float(g) if g is not None else float("inf")
            except (TypeError, ValueError):
                return float("inf")

        scenes.sort(key=lambda x: (_gd(x), x.get("acquisition_end") or ""))
        picked = None
        picked_kind = None
        for cand in scenes:
            href, kind = self._scene_download_url(cand)
            if href:
                picked = cand
                picked_kind = kind
                break
        if not picked:
            return None
        dl_url = self._scene_download_url(picked)[0]
        props = picked.get("properties") or {}
        lic = props.get("license") or "See OpenAerialMap scene license (typically CC-BY)"
        meta_uri = picked.get("meta_uri")
        scene_url = meta_uri if isinstance(meta_uri, str) and meta_uri.startswith("http") else dl_url
        return {
            "uuid": picked.get("uuid"),
            "url": dl_url,
            "download_kind": picked_kind,
            "gsd": picked.get("gsd"),
            "date": picked.get("acquisition_end"),
            "provider": picked.get("provider"),
            "license": lic,
            "scene_page_url": scene_url,
            "tiles_url": props.get("tms"),
            "thumbnail_url": props.get("thumbnail"),
        }

if __name__ == "__main__":
    # Test for Oklahoma coordinates
    # harvester = OAMHarvester()
    # print(harvester.get_best_image(35.3917, -97.9229))
    pass
