from synnefo.db import models
from snf_django.lib.api import faults
from synnefo.api.util import get_image_dict, get_vm


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
        return get_image_dict(snapshot_id, user_id)
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
