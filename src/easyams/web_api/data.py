from abc import abstractmethod, ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import List

class InlineType(Enum):
    text = 0
    bold = 1
    italic = 2
    code = 3
    link = 4


@dataclass
class InlineBlock:
    text: str
    ref: str = ''
    type: InlineType


@dataclass
class ParagraphBlock:
    level: int = 0
    child: List[InlineBlock]


@dataclass
class ListBlock:
    level: int = 0
    child: List[ParagraphBlock]


@dataclass
class CodeBlock:
    level: int = 0
    child: List[InlineBlock] = field(default_factory=lambda: [InlineBlock(type=InlineType.code)])

@dataclass
class ParamBlock:
    name: str
    desc: ParagraphBlock
    type: ParagraphBlock

@dataclass
class ReturnBlock:
    name: str
    desc: ParagraphBlock
    type: ParagraphBlock


@dataclass
class MethodBlock:
    """The rst templates
    .. method:: apply(object[, workitem][, progress])

        Apply task to specified object.

        :param object: Chunk or Document object to be processed.
        :type object: Chunk or Document
        :param workitem: Workitem index.
        :type workitem: int
        :param progress: Progress callback.
        :type progress: Callable[[float], None]
    """
    name: str  # e.g. 'apply(object[, workitem][, progress])'
    desc: str
    params: List[ParamBlock]
    returns: List[ReturnBlock]

@dataclass
class AttributeBlock:
    """RST templates:

    **Attributes**

    .. list-table::
        :header-rows: 1

        * - Variable
          - Type
          - Describtion
        * - .. attribute:: chunk
          - int
          - Chunk to copy frames from.
        * - .. attribute:: copy_dense_cloud
          - bool
          - Copy dense cloud.
        * - .. attribute:: copy_depth_maps
          - bool
          - Copy depth maps
        * - .. attribute:: copy_elevation
          - bool
          - Copy DEM.
        * - .. attribute:: copy_model
          - bool
          - Copy model.

    For each single attribute
    """
    name: str
    desc: ParagraphBlock
    type: ParagraphBlock

@dataclass
class ClassBlock:
    """The rst templates:

    .. class:: Tasks.AddFrames

        Task class containing processing parameters.

        **Methods**

        **Attributes**

    ###############################
    # For classes with subclasses:
    ###############################

    class Metashape.Tasks
    =====================

    Task classes.

    .. toctree::
    :maxdepth: 2
    :glob:
    :caption: Application Modules

    Tasks.*

    """
    name: str
    desc: List[ParagraphBlock]
    methods: List[MethodBlock]
    attributes: List[AttributeBlock]
    subclass: List['ClassBlock']
