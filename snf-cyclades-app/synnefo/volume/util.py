from synnefo.db import models
from snf_django.lib.api import faults
from synnefo.api.util import get_image_dict, get_vm, image_backend
from synnefo.cyclades_settings import cyclades_services, BASE_HOST
from synnefo.lib import join_urls
from synnefo.lib.services import get_service_path


def get_volume(user_id, volume_id, for_update=False,
               exception=faults.ItemNotFound):
    volumes = models.Volume.objects
    if for_update:
        volumes = volumes.select_for_update()
    try:
        return volumes.get(id=volume_id, userid=user_id)
    except models.Volume.DoesNotExist:
        raise exception("Volume %s not found" % volume_id)


def get_snapshot(user_id, snapshot_id, exception=faults.ItemNotFound):
    try:
        with image_backend(user_id) as b:
            return b.get_snapshot(user_id, snapshot_id)
    except faults.ItemNotFound:
        raise exception("Snapshot %s not found" % snapshot_id)


def get_image(user_id, image_id, exception=faults.ItemNotFound):
    try:
        return get_image_dict(image_id, user_id)
    except faults.ItemNotFound:
        raise exception("Image %s not found" % image_id)


def get_server(user_id, server_id, for_update=False,
               exception=faults.ItemNotFound):
    try:
        return get_vm(server_id, user_id, for_update=for_update,
                      non_deleted=True, non_suspended=True)
    except faults.ItemNotFound:
        raise exception("Server %s not found" % server_id)


VOLUME_URL = \
    join_urls(BASE_HOST,
              get_service_path(cyclades_services, "volume", version="v2.0"))

VOLUMES_URL = join_urls(VOLUME_URL, "volumes/")
SNAPSHOTS_URL = join_urls(VOLUME_URL, "snapshots/")


def volume_to_links(volume_id):
    href = join_urls(VOLUMES_URL, str(volume_id))
    return [{"rel": rel, "href": href} for rel in ("self", "bookmark")]


def snapshot_to_links(snapshot_id):
    href = join_urls(SNAPSHOTS_URL, str(snapshot_id))
    return [{"rel": rel, "href": href} for rel in ("self", "bookmark")]


def get_disk_template_provider(disk_template):
    """Extract provider from disk template.

    Provider for `ext` disk_template is encoded in the disk template
    name, which is formed `ext_<provider_name>`. Provider is None
    for all other disk templates.

    """
    provider = None
    if disk_template.startswith("ext") and "_" in disk_template:
        disk_template, provider = disk_template.split("_", 1)
    return disk_template, provider
