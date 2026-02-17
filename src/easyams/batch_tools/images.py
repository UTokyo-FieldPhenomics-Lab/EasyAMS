from ..batch_import import images as _legacy_images


def create_batch_image_importer():
    """Create the legacy batch image importer dialog."""
    return _legacy_images.create_batch_image_importer()
