import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict

import requests
from bs4 import BeautifulSoup
from cache import Cache
from gamuLogger import Logger
from version import Version

Logger.set_module("forge_reader")

RE_MC_VERSION = re.compile(r"^([0-9]+)\.([0-9]+)\.([0-9]+)$")
RE_FORGE_VERSION = re.compile(r"([0-9]+)\.([0-9]+)\.([0-9]+)(?:\.([0-9]+))?")

class JsonEncoder(json.JSONEncoder):
    def default(self, o : Any) -> str:
        if isinstance(o, Version):
            return str(o)
        elif isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

class WebInterface:
    base_url = "https://files.minecraftforge.net/net/minecraftforge/forge/"

    @staticmethod
    @Cache(expire_in=timedelta(days=1)) # type: ignore
    def get_mc_versions() -> Dict[Version, str]:
        """
        Fetches the list of Minecraft versions from the Forge website.
        """
        Logger.set_module("forge_reader.mc_versions")

        Logger.debug(f"Fetching {WebInterface.base_url} for Minecraft versions.")
        response = requests.get(WebInterface.base_url)
        if not response.ok:
            raise ConnectionError(f"Failed to fetch data from {WebInterface.base_url}. Status code: {response.status_code}")
        Logger.trace(f"Response status code: {response.status_code}")

        html_content = response.text

        Logger.trace("Scraping HTML content for Minecraft versions.")

        # find the first element with the class "sidebar-nav"
        soup = BeautifulSoup(html_content, 'html.parser')
        sidebar_nav = soup.find(class_="sidebar-nav")
        if not sidebar_nav:
            raise ValueError("No sidebar-nav found in the HTML.")
        # find all the links within the sidebar-nav
        links = sidebar_nav.find_all('a') # type: ignore
        # keep only the links where the text matches the regex
        mc_versions : dict[Version, str] = {} # version : web page relative path
        for link in links:
            if RE_MC_VERSION.match(link.text):
                Logger.debug(f"Found Minecraft version: {link.text}")
                mc_versions[Version.from_string(link.text)] = link['href'] # type: ignore

        if active := sidebar_nav.find(class_="elem-active"): # type: ignore
            version = active.text.strip()
            link = f"index_{version}.html"
            if RE_MC_VERSION.match(version):
                Logger.debug(f"Found Minecraft version: {version}")
                mc_versions[Version.from_string(version)] = link

        Logger.debug(f"Found {len(mc_versions)} Minecraft versions.")
        Logger.trace(f"Found Minecraft versions: {mc_versions}")
        return mc_versions

    @staticmethod
    @Cache(expire_in=timedelta(days=1)) # type: ignore
    def get_forge_versions(page_path : str) -> Dict[Version, dict[str, Any]]:
        """
        Fetches the content of a specific Minecraft version page.
        :param page_path: Relative path to the version page
        :return: HTML content of the page
        """
        Logger.set_module("forge_reader.forge_versions")

        Logger.debug(f"Fetching {WebInterface.base_url + page_path} for Forge versions.")

        response = requests.get(WebInterface.base_url + page_path)
        if not response.ok:
            raise ConnectionError(f"Failed to fetch data from {WebInterface.base_url + page_path}. Status code: {response.status_code}")
        Logger.trace(f"Response status code: {response.status_code}")

        Logger.trace("Scraping HTML content for Forge versions.")
        html_content = response.text
        # find element with class "download"
        soup = BeautifulSoup(html_content, 'html.parser')
        download_list = soup.find(class_="download-list") #this is a table
        # get tbody
        tbody = download_list.find('tbody') # type: ignore
        # get all rows
        rows = tbody.find_all('tr') # type: ignore

        forge_versions : dict[Version, dict[str, Any]] = {}

        for row in rows:
            data : dict[str, Any] = {}
            download_version = row.find('td', class_='download-version') # type: ignore
            promo_recommended = download_version.find('i', class_='promo-recommended') # type: ignore
            data['recommended'] = promo_recommended is not None
            promo_latest = download_version.find('i', class_='promo-latest') # type: ignore
            data['latest'] = promo_latest is not None
            bugged = download_version.find('i', class_='fa-bug') # type: ignore
            data['bugged'] = bugged is not None

            version = download_version.text.strip() # type: ignore
            version_match = RE_FORGE_VERSION.match(version)
            if not version_match:
                raise ValueError(f"Invalid Forge version format: {version}")
            version = version_match.group(0)

            download_time = row.find('td', class_='download-time') # type: ignore
            data['time'] = datetime.strptime(download_time['title'], "%Y-%m-%d %H:%M:%S") # type: ignore

            download_links = row.find('ul', class_='download-links') # type: ignore
            for link in download_links.find_all('li'): # type: ignore
                # get the one who has "Installer" in the text of the first <a> tag
                if "Installer" in link.a.text: # type: ignore
                    if info_link := link.find('a', class_='info-link'): # type: ignore
                        data['installer'] = info_link['href'] # type: ignore
                        break
            else:
                Logger.warning(f"No installer link found for forge version: {version}")
                continue
            Logger.debug(f"Found Forge version: {version}.")
            Logger.trace(f"Recommended: {data['recommended']}, Latest: {data['latest']}, Bugged: {data['bugged']}, Time: {data['time']}, Installer: {data['installer']}")

            forge_versions[Version.from_string(version)] = data

        Logger.debug(f"Found {len(forge_versions)} Forge versions.")
        return forge_versions

    @staticmethod
    @Cache(expire_in=timedelta(days=1)) # type: ignore
    def get_forge_installer_url(mc_version: Version, forge_version: Version) -> str:
        """
        Fetches the installer URL for a specific Minecraft and Forge version.
        :param mc_version: Minecraft version
        :param forge_version: Forge version
        :return: Installer URL
        """
        mc_versions = WebInterface.get_mc_versions()
        if mc_version not in mc_versions:
            raise ValueError(f"Invalid Minecraft version: {mc_version}")

        page_path = mc_versions[mc_version]
        forge_versions = WebInterface.get_forge_versions(page_path)
        if forge_version not in forge_versions:
            raise ValueError(f"Invalid Forge version: {forge_version}")

        return forge_versions[forge_version]['installer']

if __name__ == "__main__":
    # list all Minecraft versions
    mc_versions = WebInterface.get_mc_versions()
    print("Minecraft versions:")
    mc_versions = {version: page for version, page in mc_versions.items() if version >= Version(1, 7, 0)}
    for version, page in mc_versions.items():
        forge_versions = WebInterface.get_forge_versions(page)
        print(f"  {version} ({len(forge_versions)})")
