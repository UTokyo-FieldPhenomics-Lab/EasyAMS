from ..batch_import import masks as _legacy_masks


def create_batch_mask_importer():
    """Create the legacy batch mask importer dialog."""
    return _legacy_masks.create_batch_mask_importer()
