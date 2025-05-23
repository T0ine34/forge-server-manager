import os
import subprocess

from gamuLogger import Logger
from version import Version

from .properties import Properties

Logger.set_module("installer")


EULA="""#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://aka.ms/MinecraftEULA).
eula=true
"""


def set_eula(installation_dir : str) -> None:
    """
    Patch the EULA file to accept the Minecraft EULA.

    :param installation_dir: Directory where the server is installed.
    """

    eula_path = f"{installation_dir}/eula.txt"

    with open(eula_path, "w") as eula_file:
        eula_file.write(EULA)
    Logger.debug(f"EULA file created at {eula_path}.")


def set_server_properties(installation_dir : str, mc_version : Version) -> None:
    """
    Create a server.properties file with default settings.

    :param installation_dir: Directory where the server is installed.
    """

    properties_path = f"{installation_dir}/server.properties"

    properties = Properties()
    properties.save(properties_path, mc_version)
    Logger.debug(f"Server properties file created at {properties_path}.")


def get_mc_version(installer_url : str) -> Version:
    """
    Extract the Minecraft version from the installer URL.
    """
    version_str = installer_url.split("/")[-1].split("-")[1]
    return Version.from_string(version_str)


def install(installer_url : str, installation_dir : str) -> None:
    """
    Install a Minecraft server using the provided installer URL.

    :param installer_url: URL to the installer JAR file.
    :param installation_dir: Directory where the server should be installed.
    """

    Logger.info(f"Installing Minecraft server using {installer_url} to {installation_dir}.")
    os.makedirs(installation_dir, exist_ok=True)
    os.chdir(installation_dir)

    filename = installer_url.split("/")[-1]
    Logger.trace(f"Installer filename: {filename}")

    # Download the installer JAR file
    installer_path = f"/{installation_dir}/{filename}"
    Logger.trace(f"Downloading installer {installer_url} to {installer_path}.")
    subprocess.run(["curl", "-L", "-o", installer_path, installer_url], check=True, capture_output=True)
    Logger.debug(f"Installer downloaded to {installer_path}.")


    # Run the installer with Java
    Logger.trace(f"Running installer {installer_path}.")
    subprocess.run(["java", "-jar", installer_path, "--installServer"], check=True, capture_output=True)
    Logger.debug("Installer executed successfully.")

    # Remove the installer JAR file
    Logger.trace(f"Removing installer {installer_path}.")
    os.remove(installer_path)

    # Set EULA and server properties
    set_eula(installation_dir)
    set_server_properties(installation_dir, get_mc_version(installer_url))

    Logger.info("Minecraft server installation completed successfully.")


def main():
    # Example usage
    installer_url = "https://maven.minecraftforge.net/net/minecraftforge/forge/1.20.1-47.0.0/forge-1.20.1-47.0.0-installer.jar"
    installation_dir = "/var/minecraft/test"

    install(installer_url, installation_dir)
