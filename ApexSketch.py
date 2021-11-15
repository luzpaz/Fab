#!/usr/bin/env python3
"""ShopFab: A shop based design workflow."""

import os
import sys

assert sys.version_info.major == 3  # Python 3.x
assert sys.version_info.minor == 8  # Python 3.8
sys.path.extend([os.path.join(os.getcwd(), "squashfs-root/usr/lib"), "."])

from dataclasses import dataclass
import math
from typing import Any, Callable, cast, Dict, List, Optional, Tuple, Union

import FreeCAD as App  # type: ignore
import FreeCADGui as Gui  # type: ignore

from Apex import ApexBox, ApexCheck, ApexLength, ApexPoint
from FreeCAD import Placement, Rotation, Vector
from pathlib import Path  # type: ignore
import Part  # type: ignore
import PartDesign  # type: ignore
import Sketcher  # type: ignore


PartFeature = Union[Part.Circle, Part.LineSegment, Part.Point, Part.Arc]


# ApexFeature:
class ApexFeature(object):
    """Base class a schematic features."""

    # ApexFeature.__init__():
    def __init__(self, drawing: "ApexDrawing",
                 start: ApexPoint, finish: ApexPoint, name: str = "") -> None:
        """Initialize a ApexFeature."""
        if not name:
            name = start.name  # pragm: no unit cover
        self._drawing: ApexDrawing = drawing
        self._finish: ApexPoint
        self._index: int = -999
        self._origin_index: int = -999
        self._name: str = name
        self._next: ApexFeature = self
        self._previous: ApexFeature = self
        self._start: ApexPoint
        # print(f"<=>ApexFeature.__init__(*, {self._part_feature}, '{self._name}')")

    # ApexFeature.drawing():
    @property
    def drawing(self) -> "ApexDrawing":  # pragma: no unit test
        """Return the ApexFeature ApexDrawing."""
        return self._drawing  # pragma: no unit test

    # ApexFeature.finish():
    @property
    def finish(self) -> ApexPoint:  # pragma: no unit test
        """Return the ApexFeature finish point."""
        return self._finish  # pragma: no unit test

    # ApexFeature.index():
    @property
    def index(self) -> int:
        """Return the ApexFeature index."""
        assert self._index >= -1, "index is not set"
        return self._index

    # ApexFeature.index.setter():
    @index.setter
    def index(self, index: int) -> None:
        """Set the ApexFeature index."""
        if self._index >= -1:
            raise ValueError("index is already set")  # pragma: no unit test
        if index < -1:
            raise ValueError(f"index(={index} must >= -1")  # pragma: no unit test
        self._index = index

    @property
    def finish_key(self) -> int:  # pragma: no unit test
        """Return the ApexFeature Constraint key for the finish point."""
        raise NotImplementedError(f"{self}.finish_key() not implemented yet.")

    # ApexFeature.name():
    @property
    def name(self) -> str:
        """Return ApexFeature name."""
        return self._name

    # ApexFeature.next()
    @property
    def next(self) -> "ApexFeature":  # pragma: no unit test
        """Return the next ApexFeature in circular list."""
        return self._next  # pragma: no unit test

    # ApexFeature.index.setter():
    @next.setter
    def next(self, next: "ApexFeature") -> None:
        """Set the next ApexFeature in circular list."""
        self._next = next

    # ApexFeature.part_feature():
    @property
    def part_feature(self) -> PartFeature:
        """Return the PartFeature associated with ApexFeature."""
        raise NotImplementedError(f"{self}.part_feature not implmented.")

    # ApexFeature.previous():
    @property
    def previous(self) -> "ApexFeature":  # pragma: no unit test
        """Return the previous Part ApexFeature in circular list."""
        return self._previous  # pragma: no unit test

    # ApexFeature.previous.setter():
    @previous.setter
    def previous(self, next: "ApexFeature") -> None:
        """Set the previous Part ApexFeature in circular list."""
        self._previous = next

    # ApexFeature.start():
    @property
    def start(self) -> ApexPoint:  # pragma: no unit test
        """Return the ApexFeature start point."""
        return self._start  # pragma: no unit test

    @property
    def start_key(self) -> int:
        """Return the ApexFeature Constraint key for the start point."""
        raise NotImplementedError("{self.start_key() not implemented yet.}")

    # ApexFeature.type_name():
    @property
    def type_name(self) -> str:
        """Return the ApexFeature type name."""
        raise NotImplementedError("{self}.kind() not implemented yet")


# ApexArcFeature:
class ApexArcFeature(ApexFeature):
    """Represents an an arc in a sketch."""

    # ApexArcFeature.__init__():
    def __init__(self, drawing: "ApexDrawing",
                 begin: ApexPoint, apex: ApexPoint, end: ApexPoint,
                 name: str = "", tracing: str = "") -> None:
        """Initialize an ApexArcFeature."""
        # next_tracing: str = tracing + " " if tracing else ""
        trace_level: int = 0
        if tracing:
            print(f"{tracing}=>ApexArcFeature('{begin.name}', "
                  f"'{apex.name}', '{end.name}', '{name}')")
            trace_level = 0

        # Notation:
        # * Points: 1 capital letter (e.g. A, B, C, E, etc.)
        # * Line Segments: Two capital letters: (e.g IB, OB, etc.)
        # * Angles: 3 capital letters preceded by an single angle bracket (e.g. <IBO, <CJB, etc. )
        # * Vectors: Two capital letters in angle brackets, where the first letter is the
        #   start and the second letter is the end.: (e.g. <BI>, <BO>, etc.)
        # * Unit Vectors: 2 capital letters in double angle brackets: (e.g. <<BI>>, <<BO>>, etc.)
        # * Length: Two capital letters in vertical bars (e.g. |IB|, |BC|, etc.)
        # * Distance: A lower case letter (e.g. r, etc)
        #
        # Points:
        # * B represents the *begin* Point,
        # * A represents the *apex* Point of the arc
        # * E represents the *end* Point.
        # * C represents the *center* Point of the circle that the arc will be on.
        # * S represents the Point where the circle is tangent to the line IA (i.e. the arc Start):
        # * F represents the Point where the circle is tangent to the line EA (i.e. the arc Finish):
        # * M represents a "mid" Point on the line from A through C.  M is used to compute C.
        #
        # Length:
        # * r represents the arc *radius*:
        #
        # Diagram:
        # * Segments BA and EA meet at the apex point A.
        # * A circle of radius r, centered at C tangentially touches BA and EA at S and F.
        #   (By the way, J is alphabetically after I and N is alphabetically before N.)
        # * The segments CJ and CN (not drawn) are of radius length (e.g. |CJ| = |CN| = r.)
        # * The angles <JBC and <CBN are equal.
        # * The angles <CBJ and <CNB are both 90 degrees.
        # * The a M is somewhere on the line from A through C
        #
        #     B             M
        #      \            |
        #       \         **|**
        #        \      **  |  **      E
        #         \   *     |     *   /
        #          \ *      |      * /
        #           \*      C      */
        #            S      |      F
        #             *     |     *
        #              \**  |  **/
        #               \ **|** /
        #                \  |  /
        #                 \ | /
        #                  \|/
        #                   A
        #

        # The call to the parent *__init__* can not occur until after the *start* and *finish*
        # points are determined.

        # Do some initial float and variable assignments:
        deg: Callable[[float], float] = math.degrees
        epsilon: float = 1.0e-10  # Small number
        pi: float = math.pi  # Pi constant (e.g. 3.14159...)
        r: float = apex.radius
        if r < epsilon:
            raise ValueError("No Arc with zero radius.")  # pragma: no unit test

        # Define some single letter variables for the Point's:
        b: ApexPoint = begin
        a: ApexPoint = apex
        e: ApexPoint = end
        if trace_level >= 2:  # pragma: no unit cover
            print(f"{tracing}{b=}")
            print(f"{tracing}{a=}")
            print(f"{tracing}{e=}")

        def normalize_2d(point: ApexPoint) -> ApexPoint:
            """Return ApexPoint that is normalized in X and Y only."""
            x: float = float(point.x)
            y: float = float(point.y)
            length: float = math.sqrt(x * x + y * y)
            return ApexPoint(x / length, y / length)

        # Compute a bunch of values based on B, A, and E:
        ab: ApexPoint = b - a  # <AB>
        ae: ApexPoint = e - a  # <AE>
        unit_ab: ApexPoint = normalize_2d(ab)  # <<AB>>
        unit_ae: ApexPoint = normalize_2d(ae)  # <<AE>>
        unit_am: ApexPoint = normalize_2d(unit_ab + unit_ae)  # <<AM>>
        # unit_ac: ApexPoint = unit_am  # <<C>> == <<BM>> because the are on the same line.
        if trace_level >= 2:  # pragma: no unit cover
            print(f"{tracing}{ab=}")
            print(f"{tracing}{ae=}")

        # Compute the angles from A to B, M, and E:
        ab_angle: float = ab.atan2()
        am_angle: float = unit_am.atan2()
        ae_angle: float = ae.atan2()
        sac_angle: float = abs(ab_angle - am_angle) % pi  # C is co-linear with M
        if trace_level >= 2:  # pragma: no unit cover
            print(f"{tracing}{deg(ab_angle)=:.2f}deg")
            print(f"{tracing}{deg(am_angle)=:.2f}deg")
            print(f"{tracing}{deg(ae_angle)=:.2f}deg")
            print(f"{tracing}{deg(sac_angle)=:.2f}deg")

        # The points S, C, and A form a right triangle, where:
        # * Angle <ASC is 90 degrees because the circle centered on C is tangent at S (and F).
        # * |SC| = the circle radius r.
        # * |AC| is the distance from A to C.
        # * |AS| is the distance from A to S.

        # From the sine of a right triangle:
        # * |SC| = |AC| * sin(<SAC)
        # Solve for |AC| given |SC| and sin(<SAC):
        # * |AC| = |SC| / sin(<SAC) = r / sin(<SAC)
        ac_length: float = r / math.sin(sac_angle)  # |AC|
        if trace_level >= 2:  # pragma: no unit cover
            print(f"{tracing}{ac_length=:.2f}")

        # From the Pythagorean theorem:
        # * |SC|^2 + |AS|^2 = |AC|^2
        # Solve for |AS|:
        # * |AS|^2 = |AC|^2 - |SC|^2
        # * |AS| = sqrt(|AC|^2 - |SC|^2)
        # * |AS| = sqrt(|AC|^2 - r^2)  # |SC| = r
        as_length: float = math.sqrt(ac_length * ac_length - r * r)
        af_length: float = as_length  # |AS| == |AF|
        if trace_level >= 2:  # pragma: no unit cover
            print(f"{tracing}{as_length=:.2f}")
            print(f"{tracing}{af_length=:.2f}")

        # Compute C, S, and F:
        c: ApexPoint = a + unit_am * ac_length
        s: ApexPoint = a + unit_ab * as_length
        f: ApexPoint = a + unit_ae * af_length
        if trace_level >= 2:  # pragma: no unit cover
            print(f"{tracing}{c=}")
            print(f"{tracing}{s=}")
            print(f"{tracing}{f=}")

        start_angle: float = (s - c).atan2()
        finish_angle: float = (f - c).atan2()
        # The *sweep_angle* angle is the number for degrees the arc to get from *start_angle*
        # to *finish_angle*.  This angle can never span more the 180 degrees.
        sweep_angle: float = finish_angle - start_angle
        degrees180: float = pi
        degrees360: float = 2.0 * pi
        if sweep_angle > degrees180:
            sweep_angle -= degrees360  # pragma: no unit test
        elif sweep_angle <= -degrees180:
            sweep_angle += degrees360  # pragma: no unit test
        end_angle: float = start_angle + sweep_angle
        if trace_level >= 2:  # pragma: no unit cover
            print(f"{tracing}{deg(start_angle)=}deg")
            print(f"{tracing}{deg(finish_angle)=}deg")
            print(f"{tracing}{name}: {deg(finish_angle - start_angle)=}deg")
            print(f"{tracing}{deg(sweep_angle)=}deg")
            print(f"{tracing}{deg(end_angle)=}deg")
        part_circle: Part.Circle = Part.Circle(App.Vector(c.x, c.y, 0.0), App.Vector(0, 0, 1), r)

        # After a bunch of trial and error, it was discovered that the *start_angle* and *end_angle*
        # need to be swapped to deal with a negative sweep angle.  This causes the right arc
        # to be rendered properly, but has now swapped the start/finish as far as constraints
        # are concerned.
        if sweep_angle < 0.0:
            start_angle, end_angle = end_angle, start_angle
        part_arc: Part.Arc = Part.ArcOfCircle(part_circle, start_angle, end_angle)

        # Now we can create the *ApexArcFeature*:
        super().__init__(drawing, s, f, name)
        self._apex: ApexPoint = apex
        self._begin: ApexPoint = begin
        self._center: ApexPoint = c
        self._end: ApexPoint = end
        self._finish: ApexPoint = f
        self._finish_angle: float = finish_angle
        self._finish_length: float = af_length
        self._part_arc: Part.Arc = part_arc
        self._radius: float = r
        self._start: ApexPoint = s
        self._sweep_angle: float = sweep_angle
        self._start_angle: float = start_angle
        self._start_length: float = as_length

        if trace_level >= 2:  # pragma: no unit cover
            print(f"{tracing}{self._apex=}")
            print(f"{tracing}{self._begin=}")
            print(f"{tracing}{self._center=}")
            print(f"{tracing}{self._end=}")
            print(f"{tracing}{self._finish=}")
            print(f"{tracing}{deg(self._finish_angle)=:.2f}deg")
            print(f"{tracing}{self._finish_length=}")
            print(f"{tracing}{self._radius=:.2f}")
            print(f"{tracing}{self._start=}")
            print(f"{tracing}{deg(self._start_angle)=:.2f}deg")
            print(f"{tracing}{self._start_length=}")
            print(f"{tracing}<=ApexArcFeature(*, {begin=}, {apex=}, {end=})")
        if tracing:
            print(f"{tracing}<=ApexArcFeature('{begin.name}', "
                  f"'{apex.name}', '{end.name}', '{name}')")

    # ApexArcFeature.repr():
    def __repr__(self) -> str:  # pragma: no unit test
        """Return ApexArcFeature string representation."""
        return f"ApexArcFeature({self._begin}, {self._apex}, {self._end})"  # pragma: no unit test

    # ApexArcFeature.apex():
    @property
    def apex(self) -> ApexPoint:
        """Return the ApexArcFeature apex ApexPoint."""
        return self._apex

    # ApexArcFeature.begin():
    @property
    def begin(self) -> ApexPoint:  # pragma: no unit test
        """Return the ApexArcFeature arc begin ApexPoint."""
        return self._begin  # pragma: no unit test

    # ApexArcFeature.center():
    @property
    def center(self) -> ApexPoint:
        """Return the ApexArcFeature arc center."""
        return self._center

    # ApexArcFeature.end():
    @property
    def end(self) -> ApexPoint:  # pragma: no unit test
        """Return the initial ApexArcFeature end ApexPoint."""
        return self._end  # pragma: no unit test

    # ApexArcFeature.finish():
    @property
    def finish(self) -> ApexPoint:
        """Return the ApexArcFeature arc finish ApexPoint."""
        return self._finish

    # ApexArcFeature.finish_key():
    @property
    def finish_key(self) -> int:
        """Return the ApexArcFeature finish Constraint key."""
        # return 2
        return 2 if self._sweep_angle < 0 else 1

    # ApexArcFeature.finish_angle():
    @property
    def finish_angle(self) -> float:  # pragma: no unit test
        """Return the ApexArcFeature arc finish angle."""
        return self._finish_angle  # pragma: no unit test

    # ApexArcFeature.finish_length():
    @property
    def finish_length(self) -> float:  # pragma: no unit test
        """Return distance from arc finish ApexPoint to the apex ApexPoint."""
        return self._finish_length  # pragma: no unit test

    # ApexArcFeature.input():
    @property
    def input(self) -> ApexPoint:  # pragma: no unit test
        """Return the initial ApexArcFeature arc start ApexPoint."""
        return self._start  # pragma: no unit test

    # ApexArcFeature.part_feature():
    @property
    def part_feature(self) -> PartFeature:
        """Return ApexArcFeature Part.Arc."""
        return self._part_arc

    # ApexArcFeature.radius():
    @property
    def radius(self) -> float:
        """Return the initial ApexArcFeature radius."""
        return self._radius

    # ApexArcFeature.start():
    @property
    def start(self) -> ApexPoint:
        """Return the ApexArcFeature arc start ApexPoint."""
        return self._start

    # ApexArcFeature.start_angle():
    @property
    def start_angle(self) -> float:  # pragma: no unit test
        """Return the ApexArcFeature arc start angle."""
        return self._start_angle  # pragma: no unit test

    # ApexArcFeature.start_key():
    @property
    def start_key(self) -> int:
        """Return the ApexArcFeature finish Constraint key."""
        # return 1
        return 1 if self._sweep_angle < 0.0 else 2

    # ApexArcFeature.start_length():
    @property
    def start_length(self) -> float:  # pragma: no unit test
        """Return the ApexArcFeature distance from start ApexPoint to apex ApexPoint."""
        return self._start_length  # pragma: no unit test

    # ApexArcFeature.sweep_angle():
    @property
    def sweep_angle(self) -> float:  # pragma: no unit cover
        """Return the ApexArcFeature sweep angle from start angle to end angle."""
        return self._sweep_angle

    # ApexArcFeature.type_name():
    @property
    def type_name(self) -> str:  # pragma: no unit cover
        """Return the ApexArcFeature type name."""
        return "ApexArcFeature"


# ApexCircleFeature:
class ApexCircleFeature(ApexFeature):
    """Represents a circle in a sketch."""

    # ApexCircleFeature.__init__():
    def __init__(self, drawing: "ApexDrawing",
                 center: ApexPoint, radius: float, name: str = "") -> None:
        """Initialize a ApexCircleFeature."""
        super().__init__(drawing, center, center, name)
        self._center: ApexPoint = center
        self._drawing: ApexDrawing = drawing
        self._part_circle: Part.Circle = Part.Circle(center.vector, App.Vector(0, 0, 1), radius)
        self._radius: float = radius

    # ApexCircleFeature.center():
    @property
    def center(self) -> ApexPoint:  # pragma: no unit cover
        """Return the ApexCircleFeature center."""
        return self._center

    # ApexCircleFeature.part_element():
    @property
    def part_feature(self) -> PartFeature:
        """Return the ApexCircleFeature PartFeature."""
        return self._part_circle

    # ApexCircleFeature.radius():
    @property
    def radius(self) -> float:  # pragma: no unit cover
        """Return the ApexCircleFeature radius."""
        return self._radius

    # ApexCircleFeature.type_name():
    @property
    def type_name(self) -> str:  # pragma: no unit cover
        """Return the ApexCircleFeature type name."""
        return "ApexCircleFeature"


# ApexLineFeature:
class ApexLineFeature(ApexFeature):
    """Represents a line segment in a sketch."""

    # ApexLineFeature.__init__():
    def __init__(self, drawing: "ApexDrawing",
                 start: ApexPoint, finish: ApexPoint, name: str = "", tracing: str = "") -> None:
        """Initialize a ApexLineFeature."""
        if tracing:
            print(f"{tracing}=>ApexLineFeature('{start.name}', '{finish.name}', '{name}')")
        super().__init__(drawing, start, finish, name)
        self._drawing: ApexDrawing = drawing
        self._line_segment: Part.LineSegment = Part.LineSegment(start.vector, finish.vector)
        self._start: ApexPoint = start
        self._finish: ApexPoint = finish
        if tracing:
            print(f"{tracing}<=ApexLineFeature('{start.name}', '{finish.name}', '{name}')")

    # ApexLineFeature.drawing():
    @property
    def drawing(self) -> "ApexDrawing":  # pragma: no unit cover
        """Return the ApexLineFeature ApexDrawing."""
        return self._drawing

    # ApexLineFeature.part_feature():
    @property
    def part_feature(self) -> PartFeature:
        """Return the PartFeature associated with a ApexLineFeature."""
        return self._line_segment

    # ApexLineFeature.finish():
    @property
    def finish(self) -> ApexPoint:  # pragma: no unit cover
        """Return the ApexLineFeature finish ApexPoint."""
        return self._finish

    # ApexLineFeature.finish_key():
    @property
    def finish_key(self) -> int:
        """Return the ApexLineFeature finish Constraint key."""
        return 2  # 2 => End point (never changes for a ApexLineFeature)

    # ApexLineFeature.start():
    @property
    def start(self) -> ApexPoint:
        """Return the ApexLineFeature start ApexPoint."""
        return self._start

    # ApexLineFeature.start_key():
    @property
    def start_key(self) -> int:
        """Return the ApexLineFeature start Constraint key."""
        return 1  # 1 => End point (never changes for a ApexLineFeature)

    # ApexLineFeature.type_name():
    @property
    def type_name(self) -> str:  # pragma: no unit cover
        """Return the ApexLineFeature type name."""
        return "ApexLineFeature"


# ApexPointFeature:
class ApexPointFeature(ApexFeature):
    """Represents a point in a sketch."""

    # ApexPointFeature.__init__():
    def __init__(self, drawing: "ApexDrawing", point: ApexPoint, name: str = "") -> None:
        """Initialize a ApexPointFeature."""
        super().__init__(drawing, point, point, name)
        self._point: ApexPoint = point
        self._part_point: Part.ApexPoint = Part.Point(point.vector)
        # print(f"ApexPointFeature.__init__({point.vector=}): ")

    # ApexPointFeature.__str__():
    def __str__(self) -> str:  # pragma: no unit cover
        """Return ApexPointFeature string ."""
        return f"ApexPointFeature(point={self._point}, name='{self._name}', index={self._index})"

    # ApexPointFeature.part_feature():
    @property
    def part_feature(self) -> PartFeature:
        """Return the  ApexPointFeature."""
        return self._part_point

    # ApexPointFeature.point():
    @property
    def point(self) -> ApexPoint:  # pragma: no unit cover
        """Return the ApexPointFeature ApexPoint."""
        return self._point

    # ApexPointFeature.type_name():
    @property
    def type_name(self) -> str:  # pragma: no unit cover
        """Return the ApexPointFeature type name."""
        return "ApexPointFeature"


# ApexElementKey():
@dataclass(frozen=True, order=True)
class ApexElementKey(object):
    """ApexElementKey: Sorting key for ApexElement's.

    Attributues:
    * *is_exterior* (bool): True if ApexElement is the exterior.
    * *depth* (float): The ApexElement depth.
    * *diameter* (float): The ApexCircle diameter (or 0.0 for an ApexPolygon).

    An ApexElementKey is used to group ApexElements and choose between Pad, Pocket, and
    Hole operations.

    """

    is_exterior: bool
    diameter: float
    depth: float


# ApexElement():
class ApexElement(object):
    """ApexElement: Base class for ApexCircle and ApexPolygon.

    Attributes:
    * *box* (ApexBox): The Apex box for the ApexElement.
    * *depth* (Union[float, ApexLength]): The element depth.
    * *diameter* (Union[float, ApexLength]): The element diameter.
    * *is_exterior* (bool): True if ApexElement is the exterior.
    * *key* (ApexElementKey): The grouping key FreeCAD Part Design operations.
    * *name* (Optional[str]): The ApexElement name:

    """

    # ApexElement.__init__():
    def __init__(self, is_exterior: bool = False, depth: Union[float, ApexLength] = 0.0,
                 diameter: Union[float, ApexLength] = 0.0, name: str = "") -> None:
        """Initialize the ApexElement.

        Arguments:
        * *is_exterior* (bool): True if the Element is the exterior of an ApexDrawing.
        * *depth* (Union[float, ApexLength]): The ApexElement depth.
        * *diameter* (Union[float, ApexLength]): The ApexElement diameter (0.0 for ApexPolygon.)
        * *depth* (Union[float, ApexLength]): The ApexElement depth.
        * *name* (str): The ApexElement name (Default: "").

        """
        self._is_exterior: bool = is_exterior
        self._depth: Union[float, ApexLength] = depth
        self._diameter: Union[float, ApexLength] = diameter
        self._key: ApexElementKey = ApexElementKey(
            is_exterior=is_exterior, depth=float(depth), diameter=float(diameter))
        self._name: str = name

    @property
    def box(self) -> ApexBox:
        """Return ApexBox for ApexElement."""
        raise NotImplementedError()

    @property
    def depth(self) -> Union[float, ApexLength]:
        """Return ApexElement depth."""

    @property
    def diameter(self) -> Union[float, ApexLength]:
        """Return the name."""
        return self._diameter

    @property
    def is_exterior(self) -> bool:
        """Return True if ApexElement is the exterior."""
        return self._is_exterior

    @property
    def key(self) -> ApexElementKey:
        """Return the associated ApexElementKey."""
        return self._key

    @property
    def name(self) -> str:
        """Return the name."""
        return self._name

    # ApexElement.constraints_append():
    def constraints_append(self, drawing: "ApexDrawing", constraints: List[Sketcher.Constraint],
                           tracing: str = "") -> None:
        """Append the ApexElement constraints to drawing.

        Arguments:
        * *drawing* (ApexDrawing): The drawing to use.
        * *constraints* (List[SketcherConstraint]): The contstraints list to append to.

        """
        raise NotImplementedError()

    # ApexElement.features_get():
    def features_get(self, drawing: "ApexDrawing", tracing: str = "") -> Tuple[ApexFeature, ...]:
        """Return the ApexElement ApexFeatures tuple.

        Arguments:
        * *drawing* (ApexDrawing): The associated drawing to use for feature extraction.

        Returns:
        * (Tuple[ApexFeature, ...]) of extracted ApexFeature's.

        """
        raise NotImplementedError()

    # ApexElement.reorient():
    def reorient(self, placement: Placement, suffix: Optional[str] = "",
                 tracing: str = "") -> "ApexElement":
        """Return a new reoriented ApexCircle.

        Arguments:
        * *placement* (Placement): The FreeCAD Placement reoirient with.
        * *suffix* (str): The suffix to append to the current name string.  None, specifies
          that an empty name is to be used.  (Default: "")

        # Returns:
        * (ApexElement) that has been reoriented with a new name.
        """
        raise NotImplementedError()

    # ApexElement.show():
    def show(self) -> str:
        """Return compact string for ApexElement."""
        raise NotImplementedError()


# ApexPolygon:
class ApexPolygon(ApexElement):
    """ApexPolyon: A closed polygon of ApexPoints.

    Attributes:
    * *box* (ApexBox): The bounding box of the ApexPoint's.
    * *clockwise* (bool): True if the ApexPoints are clockwise and False otherwise.
    * *depth* (Union[float, ApexLength]): The ApexPolygon depth.
    * *diameter* (Union[Float, ApexLength]): Always 0.0 for an ApexPolygon.
    * *name* (str): The ApexPolygon name.
    * *points* (Tuple[ApexPoint, ...]): The ApexPoint's of the ApexPoloygon.

    """

    INIT = (
        ApexCheck("points", ("T+", ApexPoint)),
        ApexCheck("depth", (float, ApexLength)),
        ApexCheck("is_exterior", (bool,)),
        ApexCheck("name", (str,)),
    )

    # ApexPolygon.__init__():
    def __init__(
            self,
            points: Tuple[ApexPoint, ...],
            depth: Union[ApexLength, float] = 0.0,
            is_exterior: bool = False,
            name: str = "",
            tracing: str = ""
    ) -> None:
        """Initialize a ApexPolygon."""
        arguments: Tuple[Any] = cast(Tuple[Any], (points, depth, is_exterior, name))
        value_error: str = ApexCheck.check(arguments, ApexPolygon.INIT)
        if value_error:
            assert False, str(value_error)
            raise ValueError(value_error)
        # next_tracing: str = tracing + " " if tracing else ""
        if tracing:
            print(f"{tracing}=>ApexPolygon.__init__(*, ...)")
        point: ApexPoint
        if not points:
            raise ValueError("bounding box needs at least one point.")  # pragma: no unit cover
        if float(depth) < 0.0:
            raise ValueError(f"depth {depth} is negative")

        super().__init__(is_exterior=is_exterior, diameter=0.0, depth=depth, name=name)
        self._box: ApexBox = ApexBox(points)
        self._depth: Union[ApexLength, float] = depth
        self._features: Optional[Tuple[ApexFeature, ...]] = None
        self._points: Tuple[ApexPoint, ...] = points
        if tracing:
            print(f"{tracing}<=ApexPolygon.__init__(*)=>{self.show()}")

    def __repr__(self) -> str:
        """Return string representation of ApexPolygon."""
        return self.__str__()

    def __str__(self, short: bool = False) -> str:
        """Return string representation of ApexPolygon.

        Arguments:
        * *short* (bool): If true, a shorter versions returned.

        """
        return f"ApexPolygon(({self._points}), {self._depth}, {self.is_exterior}, '{self._name}')"

    # ApexPolygon.show():
    def show(self) -> str:
        """Return compact string showing ApexPolygon contents."""
        point: ApexPoint
        points_text: str = ", ".join([f"({point.x},{point.y},{point.z})"
                                     for point in self._points])
        return f"ApexPolygon(({points_text}), {self._depth}, {self.is_exterior}, '{self._name}')"

    @property
    def box(self) -> ApexBox:
        """Return the ApexPolygon ApexBox."""
        return self._box

    # ApexPolygon.clockwise():
    @property
    def clockwise(self) -> bool:    # pragma: no unit cover
        """Return whether the ApexPolygon points are clockwise."""
        points: Tuple[ApexPoint, ...] = self._points
        points_size: int = len(points)
        index: int
        start: ApexPoint
        total_angle: float = 0.0
        for index, start in enumerate(points):
            finish: ApexPoint = points[(index + 1) % points_size]
            total_angle += math.atan2(finish.y - start.y, finish.x - start.x)
        return total_angle >= 0.0

    # ApexPolygon.constraints_append():
    def constraints_append(self, drawing: "ApexDrawing", constraints: List[Sketcher.Constraint],
                           tracing: str = "") -> None:
        """Return the ApexPolygon constraints for a ApexDrawing."""
        # Perform an requested *tracing*:
        # next_tracing: str = tracing + " " if tracing else ""
        if tracing:
            print(f"{tracing}=>ApexPolygon.contraints_append('{self.name}', "
                  f"*, {len(constraints)=}):")

        origin_index: int = drawing.origin_index
        features: Optional[Tuple[ApexFeature, ...]] = self._features
        assert features, "ApexFeatures not set"
        features_size: int = len(features)
        # degrees45: float = math.pi / 4.0
        # degrees135: float = 3.0 * degrees45
        # deg: Callable[[float], float] = math.degrees

        at_index: int
        # Iterate through adjacent ApexFeature pairs and apply constraints;
        for at_index, at_feature in enumerate(features):
            # Grab a bunch of field from *at_feature* and *before_feature*
            at_feature_index: int = at_feature.index
            at_name: str = at_feature.name
            at_start: ApexPoint = at_feature.start
            at_start_key: int = at_feature.start_key
            before_feature: ApexFeature = features[(at_index - 1) % features_size]
            before_feature_index: int = before_feature.index
            before_name: str = before_feature.name
            # before_finish: ApexPoint = before_feature.finish
            before_finish_key: int = before_feature.finish_key
            after_feature: ApexFeature = features[(at_index + 1) % features_size]
            assert at_feature is not before_feature
            if tracing:
                print("")
                print(f"{tracing}[{at_index}]: "
                      f"at={at_feature.type_name}('{at_name}'):{at_feature_index} "
                      f"before={before_feature.type_name}('{before_name}'):{before_feature_index}")

            # Extract *at_arc* and/or *before_arc* if they are present:
            before_arc: Optional[ApexArcFeature] = None
            if isinstance(before_feature, ApexArcFeature):
                before_arc = before_feature
            at_arc: Optional[ApexArcFeature] = None
            if isinstance(at_feature, ApexArcFeature):
                at_arc = at_feature
            after_arc: Optional[ApexArcFeature] = None
            if isinstance(after_feature, ApexArcFeature):
                after_arc = after_feature

            # *at_arc* almost always needs to specify a radius.  In almost all cases,
            # the X/Y coordinates of the arc center need to be specified as well.
            # There is one exception, which occurs when an arc is sandwiched between
            # two other arcs with no intervening line segments.  In this case the X/Y
            # coordinates are not needed since they will over constrain the drawing.
            if at_arc:
                at_radius: float = at_arc.radius
                at_center: ApexPoint = at_arc.center

                # Set Radius constraint:
                constraints.append(Sketcher.Constraint(
                    "Radius",
                    at_feature_index, at_radius))
                if tracing:
                    print(f"{tracing}     [{len(constraints)}]: "
                          f"Radius('{before_name}':({at_feature_index}, 0), "
                          f"{at_radius}),  # Arc Radius")

                # Suppress Arc center constraints when an arc is sandwiched between two
                # other Arcs.
                if not (before_arc and at_arc and after_arc):
                    # Set DistanceX constraint:
                    constraints.append(Sketcher.Constraint(
                        "DistanceX",
                        origin_index, 1,  # 1 => start point
                        at_feature_index, 3,  # 3 => arc center
                        at_center.x))
                    if tracing:
                        print(f"{tracing}     [{len(constraints)}]: "
                              f"DistanceX(Origin:({origin_index}, 1), "
                              f"'{at_name}':({at_feature_index},3), "
                              f"{at_center.x:.2f}) # Arc Center X")

                    # Set DistanceY constraint:
                    constraints.append(Sketcher.Constraint(
                        "DistanceY",
                        origin_index, 1,  # 1 => start point
                        at_feature_index, 3,  # 3 => arc center
                        at_center.y))
                    if tracing:
                        print(f"{tracing}     [{len(constraints)}]: "
                              f"DistanceY('Origin':({origin_index}, 1), "
                              f"'{at_name}:{at_feature_index}, 3)', "
                              f"{at_center.y:.2f}) # Arc Center Y")

            # No matter what, glue the two endpoints together.  If either side is an arc,
            # just make them tangent.  Otherwise, make the points coincident, and specify
            # an X and Y.
            if before_arc or at_arc:
                # Make coincident:
                # Just force the two features to be tangent:
                constraints.append(Sketcher.Constraint(
                    "Tangent",
                    before_feature_index, before_finish_key,
                    at_feature_index, at_start_key))
                if tracing:
                    print(f"{tracing}     [{len(constraints)}]: "
                          f"Tangent('{before_name}':({before_feature_index}, {before_finish_key}), "
                          f"'{at_name}':({at_feature_index}, {at_start_key})")
            else:
                # Specify Coincident constraint first:
                constraints.append(
                    Sketcher.Constraint(
                        "Coincident",
                        before_feature_index, before_finish_key,
                        at_feature_index, at_start_key))
                if tracing:
                    print(f"{tracing}     [{len(constraints)}]: "
                          f"Coincident('{before_name}':({before_feature_index}, "
                          f"{before_finish_key}), "
                          f"'{at_name}':({at_feature_index}, {at_start_key}) # End points")

                # Specify the DistanceX constraint next:
                constraints.append(Sketcher.Constraint(
                    "DistanceX",
                    origin_index, 1,  # 1 => start point
                    at_feature_index, at_start_key,
                    at_start.x))
                if tracing:
                    print(f"{tracing}     [{len(constraints)}]: "
                          f"DistanceX(Origin:({origin_index}, 1), "
                          f"'{at_name}:({at_feature_index}, {at_start_key})', {at_start.x:.2f})")

                # Specify DistanceY constraint last:
                constraints.append(Sketcher.Constraint(
                    "DistanceY",
                    origin_index, 1,  # 1 => start point
                    at_feature_index, at_start_key,
                    at_start.y))
                if tracing:
                    print(f"{tracing}     [{len(constraints)}]: "
                          f"DistanceY(Origin:({origin_index}, 1), "
                          f"'{at_name}({at_feature_index}, {at_start_key})', {at_start.y:.2f})")

        if tracing:
            print(f"{tracing}<=ApexPolygon.contraints_append('{self.name}', "
                  f"*, , {len(constraints)=})")

    # ApexPolygon.depth():
    @property  # pragma: no unit cover
    def depth(self) -> float:
        """Return the ApexPolygon depth."""
        return self._depth

    # ApexPolygon.features_get():
    def features_get(self, drawing: "ApexDrawing", tracing: str = "") -> Tuple[ApexFeature, ...]:
        """Return the ApexPolygon ApexFeatures tuple."""
        # This is a 4 pass process.
        #
        # In absence of any arcs, pair of points produces a single line segment where the
        # When an arc is requested, (i.e. radius > 0), an additional arc is added after
        # the line segment, where the end of the line segment shares the same point as
        # the beginning of the  arc.  In this case the preceding line segment is shortened
        # to touch where the arc is.
        #
        # Terminology:
        # * before: The point/arc/line before the current index.
        # * at: The point/arc/line at the current index.
        # * after: The point/arc/line after the current index.

        next_tracing: str = tracing + " " if tracing else ""
        if tracing:
            print(f"{tracing}=>ApexPolygon.features_get(*)")

        # Some variable declarations (re)used in the code below:
        after_point: ApexPoint
        arc: Optional[ApexArcFeature]
        at_arc: Optional[ApexArcFeature]
        at_index: int
        at_line: Optional[ApexLineFeature]
        at_name: str
        at_point: ApexPoint
        before_point: ApexPoint

        # Pass 1: Create a list of *arcs* for each point with a non-zero radius.
        # This list is 1-to-1 with the *points*.
        points: Tuple[ApexPoint, ...] = self._points
        points_size: int = len(points)
        arcs: List[Optional[ApexArcFeature]] = []
        for at_index, at_point in enumerate(points):
            before_point = points[(at_index - 1) % points_size]
            after_point = points[(at_index + 1) % points_size]
            at_name = at_point.name
            arc_feature: Optional[ApexArcFeature] = None
            if at_point.radius > 0.0:
                arc_feature = ApexArcFeature(drawing, before_point, at_point,
                                             after_point, at_name, next_tracing)
            arcs.append(arc_feature)

        # Pass 2: Create any *lines* associated with a each point.
        # This list is 1-to-1 with the points.  Occasionally, a line is omitted when 2 arcs
        # connect with no intermediate line segment.
        epsilon: float = 1e-9  # 1 nano meter (used to detect when two points are close.)
        lines: List[Optional[ApexLineFeature]] = []
        for at_index, at_point in enumerate(points):
            before_index: int = (at_index - 1) % points_size
            before_point = points[before_index]
            before_arc: Optional[ApexArcFeature] = arcs[before_index]
            at_arc = arcs[at_index]
            at_name = at_point.name

            # *start* and *finish* are the start and end points of the *line*:
            start: ApexPoint = before_arc.finish if before_arc else before_point
            finish: ApexPoint = at_arc.start if at_arc else at_point

            # There is possibility that the *before_arc* and *at_arc* could touch one another
            # without an intervening line segment.  Also, it is possible that the arc completely
            # occludes its preceding line segment.  In both cases, the preceding line segment
            # is suppressed.
            generate_at_line: bool = True
            if before_arc and at_arc:
                line_length: float = (before_point - at_point).magnitude()
                # *arc_lengths* is the total amount of line
                before_length: float = (before_arc.finish - before_arc.apex).magnitude()
                at_length: float = (at_arc.start - at_arc.apex).magnitude()
                arc_lengths: float = before_length + at_length
                if abs(arc_lengths - line_length) < epsilon:
                    # We have "exact" match, so the line segment is suppressed.
                    generate_at_line = False
                elif arc_lengths > line_length:  # pragma: no unit cover
                    raise ValueError("Arcs are too big")
            line_feature: Optional[ApexLineFeature] = None
            if generate_at_line:
                line_feature = ApexLineFeature(drawing, start,
                                               finish, at_name, tracing=next_tracing)
            lines.append(line_feature)

        # Pass 3: Assemble the final *features* list:
        features: List[ApexFeature] = []
        for at_index in range(points_size):
            at_line = lines[at_index]
            if at_line:
                features.append(at_line)
            at_arc = arcs[at_index]
            if at_arc:
                features.append(at_arc)
        final_features: Tuple[ApexFeature, ...] = tuple(features)

        # Pass 4: Make bi-directional doubly linked list features that is used for constraints
        # generation.
        at_feature: ApexFeature
        features_size: int = len(features)
        for at_index, feature in enumerate(final_features):
            feature.previous = features[(at_index - 1) % features_size]
            feature.next = features[(at_index + 1) % features_size]

        self._features = final_features
        if tracing:
            print(f"{tracing}<=ApexPolygon.features_get(*)=>|*|={len(final_features)}")
        return final_features

    # ApexPolygon.name():
    @property
    def name(self) -> str:  # pragma: no unit cover
        """Return the ApexPolygon depth."""
        return self._name

    # ApexPolygon.points():
    @property
    def points(self) -> Tuple[ApexPoint, ...]:  # pragma: no unit cover
        """Return the ApexPolygon points."""
        return self._points

    REORIENT_CHECKS = (
        ApexCheck("placement", (Placement,)),
        ApexCheck("suffix", (str, )),
    )

    # ApexPolygon.reorient():
    def reorient(self, placement: Placement, suffix: Optional[str] = "",
                 tracing: str = "") -> "ApexPolygon":
        """Reorient an ApexPolygon with a new Placement.

        Arguments:
        * *placement* (Placement):
          The FreeCAD Placement to use for reorientation.
        * *suffix* (Optional[str]):
          A suffix to append to the name.  If None, an empty name is used. (Default: "")

        """
        arguments: Tuple[Any, ...] = (placement, suffix)
        value_error: str = ApexCheck.check(arguments, ApexPolygon.REORIENT_CHECKS)
        if value_error:
            raise ValueError(value_error)
        if tracing:
            print(f"{tracing}=>ApexPolygon.reorient{arguments}")

        name: str = f"{self._name}{suffix}" if suffix else ""
        apex_point: ApexPoint
        reoriented_points: Tuple[ApexPoint, ...] = tuple([
            apex_point.reorient(placement, name) for apex_point in self.points])
        result: ApexPolygon = ApexPolygon(reoriented_points, depth=self._depth,
                                          is_exterior=self._is_exterior, name=name)
        if tracing:
            index: int
            for index, apex_point in enumerate(self._points):
                print(f"{tracing}Point[{index}]:{apex_point.vector} => "
                      f"{reoriented_points[index].vector}")
            print(f"{tracing}<=ApexPolygon.reorient{arguments}=>*")
        return result


# ApexCircle:
class ApexCircle(ApexElement):
    """ApexCircle: Represents a circle with an optional hole.

    Attributes:
    * *box* (ApexBoundBox): The ApexCircle ApexBoundBox.
    * *center* (ApexPoint): The center of the circle.
    * *circle_feature* (ApexCircleFeature): The ApexCircleFeature for the circle.
    * *depth* (float): The hole depth in millimeters.
    * *flat* (bool): True if the hole bottom is flat.
    * *is_exterior* (bool): True if the ApexCircle is the exterior of an ApexDrawing.
    * *name* (str): The ApexCircle name.
    * *radius* (str): The ApexCircle radius in millimeters.

    """

    # ApexCircle.__init():
    def __init__(
            self,
            center: ApexPoint,
            depth: float = 0.0,
            flat: bool = False,
            is_exterior: bool = False,
            name: str = ""
    ) -> None:
        """Initialize a circle."""
        if center.radius <= 0:
            raise ValueError("ApexCircle has no radius")  # pragma: no unit cover

        name = name if name else center.name
        super().__init__(is_exterior=is_exterior, depth=depth, diameter=center.diameter, name=name)
        x: float = center.x
        y: float = center.y
        radius: float = center.radius

        lower: ApexPoint = ApexPoint(x - radius, y - radius, 0.0, name=name, diameter=0.0)
        upper: ApexPoint = ApexPoint(x + radius, y + radius, 0.0, name=name, diameter=0.0)

        self._box: ApexBox = ApexBox((lower.vector, upper.vector))
        self._circle_feature: Optional[ApexCircleFeature] = None
        self._constraints: Tuple[Sketcher.Constraint, ...] = ()
        self._center: ApexPoint = center
        self._flat: bool = flat
        self._radius: float = radius

    def __repr__(self) -> str:
        """Return a string representation of ApexCircle."""
        return self.__str__()

    def __str__(self) -> str:
        """Return a string representation of ApexCircle."""
        return (f"ApexCircle({self._center}, "
                f"{self._radius}, '{self._name}')")  # pragma: no unit cover

    # ApexCircle.box():
    @property
    def box(self) -> ApexBox:
        """Return the ApexCircle ApexBox."""
        return self._box

    @property
    def center(self) -> ApexPoint:
        """Return the ApexCircle center ApexPoint."""
        return self._center

    @property
    def circle_feature(self) -> ApexCircleFeature:
        """Return the ApexCircle ApexCircleFeature."""
        circle_feature: Optional[ApexCircleFeature] = self._circle_feature
        if not circle_feature:
            raise ValueError(f"{self} does not have a feature yet.")  # pragma: no unit cover
        return circle_feature

    # ApexCircle.constraints_append():
    def constraints_append(self, drawing: "ApexDrawing", constraints: List[Sketcher.Constraint],
                           tracing: str = "") -> None:
        """Return the ApexCircleFeature constraints."""
        if tracing:
            print(f"{tracing}=>ApexCircle.constraints_append(*, *): {len(constraints)=}")
        origin_index: int = drawing.origin_index
        center: ApexPoint = self._center
        circle_feature: ApexCircleFeature = self.circle_feature
        circle_feature_index: int = circle_feature.index
        circle_name: str = self.name

        # Append the Radius constraint:
        constraints.append(Sketcher.Constraint("Radius",
                                               circle_feature_index,
                                               self.radius))
        if tracing:
            print(f"{tracing}     [{len(constraints)}]: "
                  f"Radius('{circle_name}:({circle_feature_index}, 0)'),  # Arc Radius")

        # Append the DistanceX constraint:
        constraints.append(Sketcher.Constraint("DistanceX",
                                               origin_index, 1,  # 1 => Start point
                                               circle_feature_index, 3,  # 3 => ApexCircle Center
                                               center.x))
        if tracing:
            print(f"{tracing}     [{len(constraints)}]: "
                  f"DistanceX(Origin:({origin_index}, 1), "
                  f"'{circle_name}':({circle_feature_index}, 3), "
                  f"{center.x:.2f})) # ApexCircle Center X")

        # Append the DistanceY constraint:
        constraints.append(
            Sketcher.Constraint("DistanceY",
                                origin_index, 1,  # 1 => Start ApexPoint
                                circle_feature_index, 3,  # 3 => ApexCircle Center
                                center.y))
        if tracing:
            print(f"{tracing}     [{len(constraints)}]: "
                  f"DistanceX(Origin:({origin_index}, 1), "
                  f"'{circle_name}':({circle_feature_index}, 3), "
                  f"{center.y:.2f})) # ApexCircle Center Y")
            print(f"{tracing}<=ApexCircle.constraints_append(*, *): {len(constraints)=}")

    @property
    def depth(self) -> float:
        """Return the ApexCircle Depth."""
        return self._depth

    @property
    def flat(self) -> bool:
        """Return whether the ApexCircle bottom is flat."""
        return self._flat

    # ApexCircle.features_get():
    def features_get(self, drawing: "ApexDrawing", tracing: str = "") -> Tuple[ApexFeature, ...]:
        """Return the ApexCircleFeature."""
        if tracing:
            print(f"{tracing}=>ApexCircle.features_get()")
        circle_feature: Optional[ApexCircleFeature] = self._circle_feature
        if not circle_feature:
            circle_feature = ApexCircleFeature(drawing, self.center, self.radius, self.name)
            self._circle_feature = circle_feature
        if tracing:
            print(f"{tracing}<=ApexCircle.features_get()=>{(circle_feature,)}")
        return (circle_feature,)

    @property
    def name(self) -> str:
        """Return the name of the ApexCircle."""
        return self._name

    @property
    def radius(self) -> float:
        """Return the ApexCircle radius."""
        return self._radius

    # ApexCircle.reorient():
    def reorient(self, placement: Placement, suffix: Optional[str] = "",
                 tracing: str = "") -> "ApexCircle":
        """Return a new reoriented ApexCircle.

        Arguments:
        * *placement* (Placement): The FreeCAD Placement reoirient with.
        * *suffix* (str): The suffix to append to the current name string.  None, specifies
          that an empty name is to be used.  (Default: "")

        """
        if tracing:
            print(f"{tracing}=>ApexCircle.reorient(*, {placement}, '{suffix}')")
        name: str = f"{self.name}{suffix}" if suffix else ""
        reoriented: ApexCircle = ApexCircle(
            center=self.center.reorient(placement, suffix), depth=self.depth, flat=self.flat,
            is_exterior=self.is_exterior, name=name)
        if tracing:
            print(f"{tracing}{self} => {reoriented}")
            print(f"{tracing}<=ApexCircle.reorient(*, {placement}, '{suffix}') => *")
        return reoriented


# ApexDrawing:
class ApexDrawing(object):
    """ApexDrawing: Used to create fully constrained 2D drawings.

    Attributes:
    * *contact*: (Union[Vector, ApexPoint]): On point on the surface of the polygon.
    * *normal*: (Union[Vector, ApexPoint]): A normal to the polygon plane.
    * *elements* (Tuple[ApexElement, ...]): All ApexElements (including *exterior*, if present.)
    * *exterior* (Optional[ApexElement]): The exterior ApexElement, if present (Default: None).
    * *name* (str): The ApexDrawing name. (Default: "")

    """

    INIT_CHECKS = (
        ApexCheck("contact", (Vector, ApexPoint)),
        ApexCheck("normal", (Vector, ApexPoint)),
        ApexCheck("elements", ("T", ApexElement)),
        ApexCheck("exterior", ("?", ApexElement)),
        ApexCheck("name", (str,)),
    )

    # ApexDrawing.__init__():
    def __init__(
            self,
            contact: Union["ApexPoint", "Vector"],
            normal: Union["ApexPoint", "Vector"],
            elements: Tuple[ApexElement, ...],
            exterior: Optional[ApexElement] = None,
            name: str = "",
            tracing: str = ""
    ) -> None:
        """Initialize a drawing.

        Arguments:
        * *contact* (Union[ApexPoint, Vector]):
          A point on the surface of the drawing in 3D space.  (Default: Vector(0, 0, 0))
        * *normal* (Union[ApexPoint, Vector]):
          An ApexPoint/Vector that is normal to the plane that goes through *contact*.
          (Default: Vector(0, 0, 1))
        * *exterior*: (Optional[ApexElement]):
          The exterior contour of the part.  None if exterior is not needed. (Default: None)
        * *name*: (str): The drawing name.  (Default: "")

        Raises:
        * ValueError if no exterior, circles, or polygons are specified.

        """
        arguments: Tuple[Any, ...] = (contact, normal, elements, exterior, name)
        value_error: str = ApexCheck.check(arguments, ApexDrawing.INIT_CHECKS)
        if value_error:
            raise ValueError(value_error)
        trace_arguments: str
        if tracing:
            trace_arguments = (
                f"ApexDrawing.__init__(({contact.x}, {contact.y}, {contact.z}), "
                f"({normal.x}, {normal.y}, {normal.z}), *, '{name}')"
            )
            print(f"{tracing}=>{trace_arguments}")
        if not elements:
            raise ValueError(f"No ApexPolygon's or ApexCircle's provided.")
        if exterior and exterior not in elements:
            raise ValueError(f"Exterior element not present in elements.")
        if exterior and exterior.depth <= 0:
            raise ValueError(f"Exterior element does not have a positive depth")
        # next_tracing: str = tracing + " " if tracing else ""

        # Create the *placement* used to rotate all points around *contact* such that
        # *perpendicular* is aligned with the +Z axis:
        contact = contact.vector if isinstance(contact, ApexPoint) else contact
        assert isinstance(contact, Vector), f"{contact=}"
        normal = (normal.vector if isinstance(normal, ApexPoint) else normal)
        assert isinstance(normal, Vector)
        normal = normal.normalize()
        # rotation: Rotation = Rotation(normal, Vector(0, 0, 1))
        # placement: Placement = Placement(Vector(0, 0, 0), rotation, contact)

        # Load everything into *self* (i.e. ApexDrawing):
        # self._body: Optional[PartDesign.Body] = None
        # self._datum_plane: Optional[Part.ApexFeature] = None
        # self._geometries: List[Any] = []

        # Now compute the final *box*:
        element: ApexElement
        box: ApexBox = ApexBox([element.box for element in elements])

        # Load everything into *self*:
        self._box: ApexBox = box
        self._contact: Union[ApexPoint, Vector] = contact
        self._datum_plane_counter: int = 0
        self._elements: Tuple[ApexElement, ...] = elements
        self._exterior: Optional[ApexElement] = exterior
        self._origin_index: int = -999  # Value that is less than -1 (used for constraints)
        self._name: str = name
        self._normal: Vector = normal.normalize()  # Store in normalized form.

        if tracing:
            print(f"{tracing}<={trace_arguments}")

    @property
    def elements(self) -> Tuple["ApexElement", ...]:
        """Return the ApexDrawing Circle's."""
        return self._elements

    @property
    def name(self) -> str:
        """Return the ApexDrawing name."""
        return self._name

    @property
    def origin_index(self) -> int:
        """Return the ApexDrawing origin index."""
        origin_index: int = self._origin_index
        if origin_index < -1:
            raise ValueError(f"Origin Index not set.")  # pragma: no unit test
        return self._origin_index

    def __repr__(self) -> str:
        """Return string representation of ApexDrawing."""
        return self.__str__()

    def __str__(self) -> str:
        """Return string representation of ApexDrawing."""
        return (f"ApexDrawing({self._contact}, {self._normal}, {self._elements}, "
                f"{self._exterior}, '{self._name}')")

    # ApexDrawing.show():
    def show(self) -> str:
        """Return compact string for ApexDrawing."""
        contact: Union[ApexPoint, Vector] = self._contact
        if isinstance(contact, ApexPoint):
            contact = contact.vector
        assert isinstance(contact, Vector)
        normal: Union[ApexPoint, Vector] = self._normal
        if isinstance(normal, ApexPoint):
            contact = normal.vector
        assert isinstance(normal, Vector)

        element: ApexElement
        elements_text: str = ", ".join([f"{element.show()}" for element in self._elements])
        exterior_text: str = "None"
        if self._exterior:
            exterior_text = f"{self._exterior.show()}"
        return ("ApexDrawing("
                f"({contact.x},{contact.y},{contact.z}), ({normal.x},{normal.y},{normal.z})"
                f"({elements_text}), {exterior_text}, '{self._name}')")

    # ApexDrawing.create_datum_plane():
    def create_datum_plane(self, body: "PartDesign.Body", name: Optional[str] = None,
                           tracing: str = "") -> "Part.ApexFeature":
        """Return the FreeCAD DatumPlane used for the drawing.

        Arguments:
        * *body* (PartDesign.Body): The FreeCAD Part design Body to attach the datum plane to.
        * *name* (Optional[str]): The datum plane name.
          (Default: "...DatumPlaneN", where N is incremented.)
        * Returns:
          * (Part.ApexFeature) that is the datum_plane.
        """
        # This is where the math for FreeCAD DatumPlanes is discussed.
        #
        # Here is the notation used in this comment:
        #
        # Scalars: a, b, c, ...  (i.e. a lower case letter)
        # Vectors: P, N, Pa, ... (i.e. an upper case letter with optional suffix letter)
        # Magnitude: |N|, |P|, ... (i.e. a vector with vertical bars on each side.)
        # Unit Normal: <N>, <P>, ... (i.e. a vector enclosed in angle brakcets < ...>).)
        # Dot Product: N . P (i.e. two vectors separated by a period.)
        # Vector scaling: s * V (i.e. a scalar times a vector.)
        # Note that:  |N| * <N> = N
        #
        # The section on Hessian normal plane representation from
        # [MathWorld Planes](https://mathworld.wolfram.com/Plane.html)
        # is worth reading.
        #
        # The base coordinate system ('b' suffix) has an origin (Ob=(0,0,0)), X axis (<Xb>=(1,0,0)),
        # Y axis (<Yb>=(0,1,0), and Z axis (<Zb>=(0,1,0).
        #
        # A datum plane specifies a new coordinate system ('d' suffix) that has an Origin (Od),
        # X axis (<Xd>), Y axis (<Yd>), and Z axis (<Zd>).
        #
        # The math for computing these values is discussed immediately below:
        #
        # A plane is specified by a contact point Pd on the plane and a normal Nd to the plane.
        # The normal can be at any point on the plane.
        #
        # The datum plane origin is computed as:
        #
        #     Od = Os + d * <Nd>
        #
        # where d is a signed distance computed as:
        #
        #     d = - (<Nd> . Pd)

        # Compute *rotation* from <Zb> to <Nd>:
        if tracing:
            print(f"{tracing}=>ApexDrawing.create_datum_plane("
                  f"'{self._name}', '{body.Name}', {name})")
        contact: Vector = self._contact  # Pd
        normal: Vector = self._normal  # <Nd>
        distance: float = normal.dot(contact)  # d = - (<Nd> . Pd)
        origin: Vector = normal * distance  # Od = Os + d * <Nd>
        z_axis: Vector = Vector(0, 0, 1)  # <Zb>
        rotation: Rotation = Rotation(z_axis, normal)  # Rotation from <Zb> to <Nd>.
        if tracing:
            print(f"{tracing}{contact=}")
            print(f"{tracing}{normal=}")
            print(f"{tracing}{origin=}")
            print(f"{tracing}{rotation=}")

        # Create, save and return the *datum_plane*:
        if not name:
            name = f"{self._name}.DatumPlane{self._datum_plane_counter}"
            self._datum_plane_counter += 1
        datum_plane: Part.ApexFeature = body.newObject("PartDesign::Plane", name)
        # xy_plane: App.GeoApexFeature = body.getObject("XY_Plane")
        placement: Placement = Placement(origin, rotation)
        if tracing:
            print(f"{tracing}{placement=}")
        datum_plane.AttachmentOffset = Placement()  # Null placement:  Use Placement instead
        datum_plane.Placement = placement
        datum_plane.MapMode = "Translate"
        datum_plane.MapPathParameter = 0.0
        datum_plane.MapReversed = False
        datum_plane.Support = None
        datum_plane.recompute()

        # Turn datum plane visibility off:
        if App.GuiUp:  # pragma: no unit cover
            gui_document: Any = Gui.ActiveDocument
            object_name: str = datum_plane.Name
            gui_datum_plane: Any = gui_document.getObject(object_name)
            if gui_datum_plane is not None and hasattr(gui_datum_plane, "Visibility"):
                setattr(gui_datum_plane, "Visibility", False)

        self._datum_plane = datum_plane
        if tracing:
            print(f"{tracing}<=ApexDrawing.create_datum_plane("
                  f"'{self._name}', '{body.Name}', '{name}') => *")
        return self._datum_plane

    # ApexDrawing.plane_process():
    def plane_process(self, body: "PartDesign.Body", document_name: str, tracing: str = "") -> None:
        """Plane_Process."""
        next_tracing: str = tracing + " " if tracing else ""
        if tracing:
            print(f"{tracing}################################################################")
            print(f"{tracing}=>ApexDrawing.plane_process('{self.name}', '{body.Name}')")

        # app_document: App.Document = App.getDocument(document_name)
        gui_document: Optional[Gui.Document] = None
        if App.GuiUp:  # pragma: no unit cover
            gui_document = Gui.getDocument(document_name)

        # Create the *datum_plane*.  The "Apex" in Part.ApexFeature is a coinciding name used
        # by the FreeCAD Part Design workbench. It is not related to the Apex classes.
        # There is commonly used *datum_plane* for all sketches:
        datum_plane: Part.ApexFeature = self.create_datum_plane(body, tracing=next_tracing)

        # Partition *elements* into *groups* based on the associated *key*:
        element: ApexElement
        groups: Dict[ApexElementKey, Tuple[ApexElement, ...]] = {}
        key: ApexElementKey
        index: int
        for index, element in enumerate(self.elements):
            key = element.key
            if key not in groups:
                groups[key] = ()
            groups[key] += (element,)

        # Generate one *sketch* per *group*:
        for index, key in enumerate(sorted(groups.keys(), reverse=True)):
            if tracing:
                print("")
                print(f"{tracing}Group[{index}]: {key}")
            group: Tuple[ApexElement, ...] = groups[key]

            group0: ApexElement = group[0]

            # Deal with *exterior*:
            exterior: Optional[ApexElement] = None
            if key.is_exterior:
                if len(group) != 1:
                    raise ValueError("Exterior should be all by itself")
                exterior = group0
                if float(exterior.depth) <= 0.0:
                    raise ValueError("Exterior depth '{exterior.name}' is not positive.")

            # Create a new *drawing* using elements:
            group_name: str = f"{group0._name}_{len(group)}"
            drawing = ApexDrawing(self._contact, self._normal, group, exterior, name=group_name,
                                  tracing=next_tracing)

            # Create the *sketch* and attach it to *datum_plane*:
            sketch_name: str = f"{group0.name}.sketch"
            sketch: Sketcher.SketchObject = body.newObject("Sketcher::SketchObject", sketch_name)
            if tracing:
                print(f"{tracing}{sketch=} {sketch.Name=}")
            sketch.Support = (datum_plane, "")
            sketch.MapMode = "FlatFace"
            if App.GuiUp:
                if gui_document:  # pragma: no unit cover
                    if tracing:
                        print(f"{tracing}{sketch.Name=}")
                    gui_sketch: Any = gui_document.getObject(sketch.Name)
                    if gui_sketch and hasattr(gui_sketch, "Visibility"):
                        if tracing:
                            print(f"{tracing}Set sketch visibility to false")
                        setattr(gui_sketch, "Visibility", False)
            # visibility_set(sketch, False)

            # Fill in the *sketch* from *drawing*:
            drawing.sketch(sketch, tracing=next_tracing)

            if key.is_exterior:
                # Pad:
                pad: PartDesign.ApexFeature = body.newObject("PartDesign::Pad", f"{group_name}.Pad")
                pad.Profile = sketch
                pad.Length = float(key.depth)
                pad.Reversed = True
                # Unclear what most of these features do:
                pad.Length2 = 0
                pad.UseCustomVector = 0
                pad.Direction = (1, 1, 1)
                pad.Type = 0
                pad.UpToFace = None
                pad.Midplane = 0
                pad.Offset = 0

                if gui_document:  # pragma: no unit cover
                    visibility_set(pad, True)
                    view_object: Any = body.getLinkedObject(True).ViewObject
                    pad.ViewObject.LineColor = getattr(
                        view_object, "LineColor", pad.ViewObject.LineColor)
                    pad.ViewObject.ShapeColor = getattr(
                        view_object, "ShapeColor", pad.ViewObject.ShapeColor)
                    pad.ViewObject.PointColor = getattr(
                        view_object, "PointColor", pad.ViewObject.PointColor)
                    pad.ViewObject.Transparency = getattr(
                        view_object, "Transparency", pad.ViewObject.Transparency)
                    # The following code appears to disable edge highlighting:
                    # pad.ViewObject.DisplayMode = getattr(
                    #    view_object, "DisplayMode", pad.ViewObject.DisplayMode)

            elif isinstance(group0, ApexCircle):
                # We have bunch of ApexCircles with the same *diameter* and *depth*:
                if tracing:
                    print(f"{tracing}Hole")
                hole: PartDesign.Feature = body.newObject("PartDesign::Hole", f"{group_name}.Hole")
                if tracing:
                    print(f"{tracing}{hole=} {type(hole)=}")
                hole.Profile = sketch
                hole.DrillPointAngle = 118.00
                # hole.setExpression("Depth, "10mm")
                hole.ThreadType = 0
                hole.HoleCutType = 0
                hole.DrillPoint = group0.flat
                hole.Tapered = 0
                hole.Diameter = float(key.diameter)
                hole.Depth = float(key.depth)
                # hole.DrillPoint = u"Flat" if group0.flat else u"Angled"
            else:
                # Pocket:
                if tracing:
                    print(f"{tracing}Pocket")
                pocket: "PartDesign.Feature" = body.newObject(
                    "PartDesign::Pocket", f"{group_name}.Pocket")
                if tracing:
                    print(f"{tracing}{pocket=}")
                pocket.Profile = sketch
                pocket.Length = float(key.depth)

        if tracing:
            print(f"{tracing}<=ApexDrawing.plane_process('self._name', '{body.Name}')")

    # ApexDrawing.point_constraints_append():
    def point_constraints_append(self, point: ApexPoint, constraints: List[Sketcher.Constraint],
                                 tracing: str = "") -> None:  # REMOVE
        """Append ApexPoint constraints to a list."""
        # Now that the *origin_index* is set, is is safe to assemble the *constraints*:
        if tracing:
            print(f"{tracing}=>ApexPoint.constraints_append(*, |*|={len(constraints)})")
        origin_index: int = self.origin_index

        # Set DistanceX constraint:
        constraints.append(Sketcher.Constraint("DistanceX",
                                               -1, 1,  # -1 => OriginRoot.
                                               origin_index, 1, point.x))
        if tracing:
            print(f"{tracing}     [{len(constraints)}]: "
                  f"DistanceX('RootOrigin':(-1, 1), "
                  f"'{point.name}':({origin_index}, 1)), {point.x:.2f}")

        # Set DistanceY constraint:
        constraints.append(Sketcher.Constraint("DistanceY",
                                               -1, 1,  # -1 => OriginRoot.
                                               origin_index, 1, point.y))
        if tracing:
            print(f"{tracing}     [{len(constraints)}]: "
                  f"DistanceY('RootOrigin':(-1, 1), "
                  f"'{point.name}':({origin_index}, 1), {point.y:.2f})")
            print(f"{tracing}<=ApexPoint.constraints_append(*, |*|={len(constraints)})")

    # ApexDrawing.features_get():
    def point_features_get(self, point: ApexPoint, tracing: str = "") -> Tuple["ApexFeature", ...]:
        """Return the ApexPointFeature Feature's."""
        assert isinstance(point, ApexPoint)
        return (ApexPointFeature(self, point, point.name),)

    # ApexDrawing.reorient():
    def reorient(self, placement: Placement, suffix: Optional[str] = "",
                 tracing: str = "") -> "ApexDrawing":
        """Return a reoriented ApexDrawing.

        Arguments:
        * *placement* (Placement): The Placement to apply to internal ApexCircles and ApexPolygons.
        * *suffix* (Optional[str]): The suffix to append at all names.  If None, all
          names are set to "" instead appending the suffix.  (Default: "")

        """
        next_tracing: str = tracing + " " if tracing else ""
        if tracing:
            print(f"{tracing}=>ApexDrawing.reorient('{self._name}', {placement}, '{suffix}')")

        # Reorient *elements* and *exterior*:
        element: ApexElement
        exterior: Optional[ApexElement] = self._exterior
        exterior_index: int = -1
        if exterior:
            try:
                exterior_index = self._elements.index(exterior)
            except ValueError:  # pragma: no unit cover
                raise RuntimeError("Can not find exterior index")

        if tracing:
            index: int
            for index, element in enumerate(self._elements):
                print(f"{tracing}[{index}]:'{element.name}'")
        reoriented_elements: Tuple[ApexElement, ...] = tuple(
            [element.reorient(placement, suffix, tracing=next_tracing)
             for element in self._elements]
        )
        reoriented_exterior: Optional[ApexElement] = (
            reoriented_elements[exterior_index] if exterior_index >= 0 else None)

        # Reorient the plane *contact* point.
        contact: Union["ApexPoint", Vector] = self._contact
        reoriented_contact: Union[ApexPoint, Vector]
        if isinstance(contact, Vector):
            reoriented_contact = placement * contact
        elif isinstance(contact, ApexPoint):  # pragma: no unit cover
            reoriented_contact = contact.reorient(placement, suffix)

        # The *normal* is only rotated, not translated.
        normal: Union["ApexPoint", Vector] = self._normal
        rotation: Rotation = placement.Rotation
        reoriented_normal: Union[ApexPoint, Vector]
        if isinstance(normal, Vector):
            reoriented_normal = rotation * normal
        elif isinstance(normal, ApexPoint):  # pragma: no unit cover
            reoriented_normal = normal.reorient(Placement(Vector(), rotation), suffix)

        apex_drawing: ApexDrawing = ApexDrawing(
            reoriented_contact, reoriented_normal, reoriented_elements,
            reoriented_exterior, f"{self._name}{suffix}"
        )

        if tracing:
            print(f"{tracing}{contact=} >= {reoriented_contact}")
            print(f"{tracing}{normal=} >= {reoriented_normal}")
            for index, element in enumerate(self._elements):
                print(f"{tracing}[{index}]: {element.show()} =>")
                print(f"{tracing}     {reoriented_elements[index].show()}")
        if tracing:
            print(f"{tracing}<=ApexDrawing.reorient('{self._name}', {placement}, '{suffix}')")
        return apex_drawing

    # ApexDrawing.sketch():
    def sketch(self, sketcher: "Sketcher.SketchObject", tracing: str = "") -> None:
        """Insert an ApexDrawing into a FreeCAD SketchObject.

        Arguments:
        * sketcher (Sketcher.SketchObject): The sketcher object to use.
        """
        # Perform any requested *tracing*:
        index: int
        element: ApexElement
        next_tracing: str = tracing + " " if tracing else ""
        if tracing:
            print(f"{tracing}=>ApexDrawing.sketch('{self._name}', *)")
            for index, element in enumerate(self._elements):
                print(f"{tracing}Element[{index}]: '{element.show()}'")

        # Ensure that *contact* and *normal* are Vector's:
        contact: Union[ApexPoint, Vector] = self._contact
        if isinstance(contact, ApexPoint):
            contact = contact.vector  # pragma: no unit cover
        assert isinstance(contact, Vector)
        normal: Union[ApexPoint, Vector] = self._normal
        if isinstance(normal, ApexPoint):
            normal = contact.vector  # pragma: no unit cover
        assert isinstance(normal, Vector)

        # Rotate all features around *contact* such that *normal* is aligned with the +Z axis:
        origin: Vector = Vector(0, 0, 0)
        z_axis: Vector = Vector(0, 0, 1)
        rotation: Rotation = Rotation(normal, z_axis)
        z_aligned_placement: Placement = Placement(origin, rotation)
        if tracing:
            print(f"{tracing}{origin=} {rotation=} {contact=}")
            print(f"{tracing}{z_aligned_placement=}")
        z_aligned_drawing: "ApexDrawing" = self.reorient(
            z_aligned_placement, ".+z", tracing=next_tracing)
        if tracing:
            print(f"{tracing}{z_aligned_drawing._box=}")

        # There may be a better way of doing this, but for now, everything is moved to
        # quadrant 1 (i.e. +X/+Y quarter plane.)  This ensures that all length constraints
        # are always positive.  The drawing has a true Origin point.  In addition, there
        # is a *lower_left* point that is at the lower left corner of the drawing.  All
        # X/Y length constraints are positive numbers measured from the *lower_left* point.
        # The *lower_left* point is constrained to the true drawing origin by an X constraint
        # and Y constraint.  These two constraints can have values that can be positive,
        # negative or zero.  This will recenter the drawing to be in the correct location.

        name: str = self._name
        z_aligned_box: ApexBox = z_aligned_drawing._box
        tsw: Vector = z_aligned_box.TSW  # Lower left is along the SW bounding box edge.
        quadrant1_placement: Placement = Placement(Vector(-tsw.x, -tsw.y, 0.0), Rotation())
        if tracing:
            print(f"{tracing}here 2")
        quadrant1_drawing: "ApexDrawing" = z_aligned_drawing.reorient(
            quadrant1_placement, ".q1", tracing=next_tracing)
        if tracing:
            print(f"{tracing}here 3")

        points: Tuple[ApexPoint, ...] = (ApexPoint(tsw.x, tsw.y, 0.0, name=f"{name}.lower_left"),)
        # quadrant1_exterior: Optional[ApexElement] = quadrant1_drawing._exterior

        # Now extract all of the ApexFeature'ss:
        features: List[ApexFeature] = []

        # Extract the ApexFeature's from *points* (this must be first):
        point: ApexPoint
        for point in points:
            features.extend(self.point_features_get(point))

        elements: Tuple[ApexElement, ...] = quadrant1_drawing._elements
        for element in elements:
            features.extend(element.features_get(self))

        # The first Feature corresponds to *lower_left* and it is the "origin" for the sketch.
        lower_left_feature: ApexFeature = features[0]
        assert isinstance(lower_left_feature, ApexPointFeature)

        # Set the *index* for each Feature in *final_features*:
        feature: ApexFeature
        for index, feature in enumerate(features):
            feature.index = index
        final_features: Tuple[ApexFeature, ...] = tuple(features)

        # Now that the Feature indices are set, *origin_index* can be extracted:
        origin_index: int = lower_left_feature.index
        self._origin_index = origin_index
        if tracing:
            print(f"{tracing}{origin_index=}")

        # Extract *part_features* from *features*:
        part_features: List[PartFeature] = []
        for index, feature in enumerate(final_features):
            part_features.append(feature.part_feature)
        sketcher.addGeometry(part_features, False)

        # The *points* and *elements* Constraint's are extracted next:
        constraints: List[Sketcher.Constraint] = []
        for point in points:
            self.point_constraints_append(point, constraints)
        for element in elements:
            element.constraints_append(self, constraints)

        # Load the final *constraints* into *sketcher*:
        sketcher.addConstraint(constraints)

        if tracing:
            print(f"{tracing}<=ApexDrawing.sketch('{self._name}', *)")


def visibility_set(element: Any, new_value: bool = True, tracing: str = "") -> None:
    """Set the visibility of an element.

    Arguments:
    * *element* (Any): Any FreeCAD element.
    * *new_value* (bool): The new visibility to use.  (Default True):

    """
    if tracing:
        print(f"{tracing}=>visibility_set({element}, {new_value})")
    if App.GuiUp:   # pragma: no unit cover
        if tracing:
            print(f"{tracing}App.GuiUp")
        gui_document: Optional[Any] = (
            Gui.ActiveDocument if hasattr(Gui, "ActiveDocument") else None)
        if tracing:
            print(f"{tracing}{gui_document=}")
            print(f"{tracing}{dir(gui_document)=}")
            print(f"{tracing}{hasattr(gui_document, 'Name')=})")
        if gui_document and hasattr(gui_document, "Name"):
            name: str = getattr(element, "Name")
            if tracing:
                print(f"{tracing}{name=}")
            sub_element: Any = gui_document.getObject(name)
            if sub_element is not None and hasattr(sub_element, "Visibility"):
                if isinstance(getattr(sub_element, "Visibility"), bool):
                    setattr(sub_element, "Visibility", new_value)
    if tracing:
        print(f"{tracing}<=visibility_set({element}, {new_value})")

    if False:  # pragma: no unit cover
        pass
        # App.getDocument('Unnamed').getObject('Body').newObject('PartDesign::Plane', 'DatumPlane')
        # App.getDocument('Unnamed').getObject('DatumPlane').Support = [
        #     (App.getDocument('Unnamed').getObject('XY_Plane'), '')]
        # App.getDocument('Unnamed').getObject('DatumPlane').MapMode = 'FlatFace'
        # App.activeDocument().recompute()
        # Gui.getDocument('Unnamed').setEdit(
        #     App.getDocument('Unnamed').getObject('Body'), 0, 'DatumPlane.')
        # Gui.Selection.clearSelection()

    if False:  # pragma: no unit cover
        # Click on [Plane face]
        pass
        # App.getDocument('Unnamed').getObject('DatumPlane').AttachmentOffset = (
        #     App.Placement(App.Vector(0.0000000000, 0.0000000000, 0.0000000000),
        #                   App.Rotation(0.0000000000, 0.0000000000, 0.0000000000)))
        # App.getDocument('Unnamed').getObject('DatumPlane').MapReversed = False
        # App.getDocument('Unnamed').getObject('DatumPlane').Support = [
        #     (App.getDocument('Unnamed').getObject('XY_Plane'), '')]
        # App.getDocument('Unnamed').getObject('DatumPlane').MapPathParameter = 0.000000
        # App.getDocument('Unnamed').getObject('DatumPlane').MapMode = 'FlatFace'
        # App.getDocument('Unnamed').getObject('DatumPlane').recompute()
        # Gui.getDocument('Unnamed').resetEdit()
        # _tv_DatumPlane.restore()
        # del(_tv_DatumPlane)


def _unit_tests() -> int:
    """Run the program."""
    # Open *document_name* and get associated *app_document* and *gui_document*:
    drawing: ApexDrawing
    center_circle: ApexCircle

    document_name: str = "ApexSketchUnitTests"
    app_document: App.Document = App.newDocument(document_name)
    # gui_document: Optional[Gui.Document] = None
    # if App.GuiUp:
    #     gui_document = Gui.GetDocument(document_name)

    # Do some trivial tests on drawing:
    try:
        drawing = ApexDrawing(Vector(), Vector(0, 0, 1), (), None, 123)  # type: ignore
    except ValueError as value_error:
        assert str(value_error) == (
            "Argument 'name' is int which is not one of ['str']"), f"{str(value_error)=}"

    # Do some unit tests on *Placment* objects to make sure they behave as documented.
    origin: Vector = Vector(0, 0, 0)
    x_axis: Vector = Vector(1, 0, 0)
    y_axis: Vector = Vector(0, 1, 0)
    z_axis: Vector = Vector(0, 0, 1)

    r0: Rotation = Rotation()
    assert r0 * origin == origin
    assert r0 * x_axis == x_axis
    assert r0 * y_axis == y_axis
    assert r0 * z_axis == z_axis

    def fix(v: Vector) -> Vector:
        return Vector(
            ApexLength.whole_fix(v.x),
            ApexLength.whole_fix(v.y),
            ApexLength.whole_fix(v.z)
        )

    rxy: Rotation = Rotation(x_axis, y_axis)
    assert rxy * x_axis == y_axis
    ryx: Rotation = Rotation(y_axis, x_axis)
    assert ryx * y_axis == x_axis

    rxz: Rotation = Rotation(x_axis, z_axis)
    assert rxz * x_axis == z_axis
    rzx: Rotation = Rotation(z_axis, x_axis)
    assert rzx * z_axis == x_axis

    ryz: Rotation = Rotation(y_axis, z_axis)
    assert ryz * y_axis == z_axis
    rzy: Rotation = Rotation(z_axis, y_axis)
    assert rzy * z_axis == y_axis

    t10: Vector = Vector(10, 10, 10)

    t10_r0_placement: Placement = Placement(t10, r0)
    assert t10_r0_placement * origin == t10
    assert t10_r0_placement * x_axis == t10 + x_axis
    assert t10_r0_placement * y_axis == t10 + y_axis
    assert t10_r0_placement * z_axis == t10 + z_axis

    t10_r0_c10_placement: Placement = Placement(t10, r0, t10)
    assert t10_r0_c10_placement * origin == t10
    assert t10_r0_c10_placement * x_axis == t10 + x_axis
    assert t10_r0_c10_placement * y_axis == t10 + y_axis
    assert t10_r0_c10_placement * z_axis == t10 + z_axis

    t0_rxy_c10_placement: Placement = Placement(origin, rxy, t10)
    assert fix(t0_rxy_c10_placement * t10) == t10, t0_rxy_c10_placement * t10
    assert fix(t0_rxy_c10_placement * (t10 + x_axis)) == t10 + y_axis

    t0_ryx_c10_placement: Placement = Placement(origin, ryx, t10)
    assert fix(t0_ryx_c10_placement * t10) == t10, t0_ryx_c10_placement * t10
    assert fix(t0_ryx_c10_placement * (t10 + y_axis)) == t10 + x_axis

    if True:
        # Create *box_polygon* (with notch in lower left corner):
        left_x: float = -40.0
        right_x: float = 40.0
        upper_y: float = 20.0
        lower_y: float = -20.0
        radius: float = 5.0
        notch_x: float = 10.0
        notch_y: float = 10.0
        lower_left_bottom: ApexPoint = ApexPoint(left_x + notch_x, lower_y, 0.0,
                                                 name="lower_left_bottom", diameter=0.0)
        lower_right: ApexPoint = ApexPoint(right_x, lower_y, 0.0,
                                           name="lower_right", diameter=0.0)
        # upper_right: ApexPoint = ApexPoint(right_x, upper_y, 0.0, "upper_right", radius)
        diameter: float = 2.0 * radius
        notch1: ApexPoint = ApexPoint(right_x, upper_y - notch_y, 0.0,
                                      name="notch1", diameter=diameter)
        notch2: ApexPoint = ApexPoint(right_x - notch_x, upper_y - notch_y, 0.0,
                                      name="notch2", diameter=diameter)
        notch3: ApexPoint = ApexPoint(right_x - notch_x, upper_y, 0.0,
                                      name="notch3", diameter=diameter)
        upper_left: ApexPoint = ApexPoint(left_x, upper_y, 0.0,
                                          name="upper_left", diameter=0.0)
        lower_left_left: ApexPoint = ApexPoint(left_x, lower_y + notch_y, 0.0,
                                               name="lower_left_left", diameter=0.0)
        box_points: Tuple[ApexPoint, ...] = (
            lower_left_bottom,
            lower_right,
            # upper_right,
            notch1,
            notch2,
            notch3,
            upper_left,
            lower_left_left,
        )
        box_polygon: ApexPolygon = ApexPolygon(box_points, depth=20.0, is_exterior=True, name="box")
        assert box_polygon.name == "box", box_polygon.name

        # Create the *hole_center*:
        center_hole: ApexPoint = ApexPoint(0.0, 0.0, 0.0, name="center_hole", diameter=10.0)
        center_circle = ApexCircle(
            center=center_hole, depth=10.0, is_exterior=False, name="center_hole")
        assert center_circle.name == "center_hole", center_circle.name

        sides: int = 4
        angle_increment: float = 2 * math.pi / float(sides)
        x_offset: float = -20.0
        y_offset: float = 5.0
        hex_radius: float = 8.0
        poly_points: List[ApexPoint] = []
        index: int
        for index in range(6):
            angle: float = index * angle_increment
            x: float = x_offset + hex_radius * math.cos(angle)
            y: float = y_offset + hex_radius * math.sin(angle)
            poly_points.append(ApexPoint(x, y, 0.0, name=f"hex{index}", diameter=0.0))
        polygon: ApexPolygon = ApexPolygon(
            tuple(poly_points), depth=18.0, is_exterior=False, name="hexagon")

        # Create the *drawing*:
        elements: Tuple[ApexElement, ...] = (box_polygon, polygon, center_circle)
        exterior: ApexPolygon = box_polygon
        drawing = ApexDrawing(origin, z_axis, elements, exterior, "test_drawing")

        # Create the FreeCAD Part Design Workbench *body* object:
        body_name: str = drawing.name if drawing.name else "Body"
        body: PartDesign.Body = app_document.addObject("PartDesign::Body", body_name)
        drawing.plane_process(body, document_name)
        visibility_set(body)
        app_document.recompute()  # This is *VERY* important!!!

    # Delete previous file *fcstd_path* and then save a new one:
    root: Path = Path("/")
    fcstd_path: Path = root / "tmp" / f"{document_name}.fcstd"
    if fcstd_path.exists():
        fcstd_path.unlink()
    print(f"Save {fcstd_path} file.")
    app_document.saveAs(f"{str(fcstd_path)}")

    # Close *document_name* and exit by closing the main window:
    App.closeDocument(document_name)
    if App.GuiUp:
        Gui.getMainWindow().close()  # pragma: no unit cover
    return 0


def class_names_show(module_object: Any) -> None:  # pragma: no unit cover
    """Show the the class name of an object."""
    print(f"module: {module_object.__name__}")
    name: str
    for name in dir(module_object):
        pass
        # attribute = getattr(module_object, name)
        # if inspect.isclass(attribute):
        #     print(f"  class: {name}")


def attributes_show(some_object: Any) -> None:  # pragma: no unit cover
    """Show the attributes of an object."""
    pass
    # name: str
    # for name in dir(some_object):
    #     if name[0] != "_":
    #         print(f"{name}: {getattr(some_object, name)}")


if __name__ == "__main__":
    _unit_tests()
