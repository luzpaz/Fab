#!/usr/bin/env python3
"""ShopFab: A shop based design workflow."""
import os
import sys

assert sys.version_info.major == 3  # Python 3.x
assert sys.version_info.minor == 8  # Python 3.8
sys.path.extend([os.path.join(os.getcwd(), "squashfs-root/usr/lib"), "."])

import math
from typing import Any, Callable, List, Optional, Tuple, Union

import FreeCAD as App  # type: ignore
import FreeCADGui as Gui  # type: ignore

from ApexBase import ApexBoundBox, ApexPose, ApexPoint
from FreeCAD import BoundBox, Vector
from pathlib import Path  # type: ignore
import Part  # type: ignore
import PartDesign  # type: ignore
import Sketcher  # type: ignore


# ApexDrawing:
class ApexDrawing(object):
    """Represents a 2D drawing."""

    # ApexDrawing.__init__():
    def __init__(
            self,
            circles: Tuple["ApexCircle", ...],
            polygons: Tuple["ApexPolygon", ...],
            name: str = ""
    ) -> None:
        """Initialize a drawing."""
        circle: ApexCircle
        circle_bounding_boxes: Tuple[ApexBoundBox, ...] = tuple([circle.bounding_box
                                                                for circle in circles])
        polygon_bounding_boxes: Tuple[ApexBoundBox, ...] = tuple([polygon.bounding_box
                                                                 for polygon in polygons])
        bounding_box: ApexBoundBox = ApexBoundBox.from_bound_boxes(
            circle_bounding_boxes + polygon_bounding_boxes)

        self._bounding_box: ApexBoundBox = bounding_box
        self._circles: Tuple[ApexCircle, ...] = circles
        self._geometries: List[Any] = []
        self._origin_index: int = -999  # Value that is less than -1
        self._name: str = name
        self._polygons: Tuple[ApexPolygon, ...] = polygons

    # ApexDrawing.bounding_box():
    @property
    def bounding_box(self) -> ApexBoundBox:
        """Return the ApexDrawing ApexBoundBox."""
        return self._bounding_box

    # ApexDrawing.circles():
    @property
    def circles(self) -> Tuple["ApexCircle", ...]:  # pragma: no unit test
        """Return the ApexDrawing Circle's."""
        return self._circles  # pragma: no unit test

    # ApexDrawing.forward_transform():
    def forward_transform(self, pose: ApexPose) -> "ApexDrawing":
        """Return an ApexDrawing that is offset via a forward transform."""
        circle: ApexCircle
        circles: Tuple[ApexCircle, ...] = tuple([circle.forward_transform(pose)
                                                 for circle in self._circles])
        polygon: ApexPolygon
        polygons: Tuple[ApexPolygon, ...] = tuple([polygon.forward_transform(pose)
                                                   for polygon in self._polygons])
        return ApexDrawing(circles, polygons, self._name)

    # ApexDrawing.name():
    @property
    def name(self) -> str:
        """Return the ApexDrawing name."""
        return self._name

    # ApexDrawing.origin_index():
    @property
    def origin_index(self) -> int:
        """Return the ApexDrawing origin index."""
        origin_index: int = self._origin_index
        if origin_index < -1:
            raise ValueError(f"Origin Index not set.")  # pragma: no unit test
        return self._origin_index

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

    # ApexDrawing.polygons():
    @property
    def polygons(self) -> Tuple["ApexPolygon", ...]:  # pragma: no unit test
        """Return the ApexDrawing ApexPolygon's."""
        return self._polygons  # pragma: no unit test

    # ApexDrawing.sketch():
    def sketch(self, sketcher: "Sketcher.SketchObject",
               lower_left: ApexPoint, tracing: str = "") -> None:
        """Sketch a ApexDrawing."""
        # Perform any requested *tracing*:
        assert isinstance(lower_left, ApexPoint)
        next_tracing: str = tracing + " " if tracing else ""
        if tracing:
            print(f"{tracing}=>ApexDrawing.sketch(*, {lower_left})")

        # Start to assemble *features from *circles*, *points*, and *polygons*:
        circles: Tuple[ApexCircle, ...] = self._circles
        points: Tuple[ApexPoint, ...] = (lower_left, )
        polygons: Tuple[ApexPolygon, ...] = self._polygons
        features: List[ApexFeature] = []

        # Extract the VectorFeature's from *points* (this must be first):
        point: ApexPoint
        for point in points:
            assert isinstance(point, ApexPoint)
            assert isinstance(point, ApexPoint)
            features.extend(self.point_features_get(point))

        # Extract the CircleFeature's from *circles*:
        circle: ApexCircle
        index: int
        for index, circle in enumerate(circles):
            features.extend(circle.features_get(self))

        # Extract the PolygonFeature's from *polygons*:
        polygon: ApexPolygon
        for index, polygon in enumerate(polygons):
            features.extend(polygon.features_get(self))

        # The first Feature corresponds to *lower_left* and it the "origin" for the sketch.
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

        # Extract *part_features* from *features* and assign an *index* to each *feature*:
        part_features: List[PartFeature] = []
        for index, feature in enumerate(final_features):
            # part_feature: PartFeature = feature.part_feature
            # print(f"part_feature[{index}]: {part_feature}")
            part_features.append(feature.part_feature)
        sketcher.addGeometry(part_features, False)

        # The *points*, *circles* and *polygons* Constraint's are extracted next:
        constraints: List[Sketcher.Constraint] = []
        for point in points:
            self.point_constraints_append(point, constraints, tracing=next_tracing)
        for circle in circles:
            circle.constraints_append(self, constraints, tracing=next_tracing)
        for polygon in polygons:
            polygon.constraints_append(self, constraints, tracing=next_tracing)

        # Load the final *constraints* into *sketcher*:
        sketcher.addConstraint(constraints)

        if tracing:
            print(f"{tracing}<=ApexDrawing.sketch(*, {lower_left})")


PartFeature = Union[Part.Circle, Part.LineSegment, Part.Point, Part.Arc]


# ApexFeature:
class ApexFeature(object):
    """Base class a schematic features."""

    # ApexFeature.__init__():
    def __init__(self, drawing: ApexDrawing,
                 start: ApexPoint, finish: ApexPoint, name: str = "") -> None:
        """Initialize a ApexFeature."""
        if not name:
            name = start.name
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
    def drawing(self) -> ApexDrawing:  # pragma: no unit test
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
    def __init__(self, drawing: ApexDrawing,
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
    def __init__(self, drawing: ApexDrawing,
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
    def __init__(self, drawing: ApexDrawing,
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
    def drawing(self) -> ApexDrawing:  # pragma: no unit cover
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
    def __init__(self, drawing: ApexDrawing, point: ApexPoint, name: str = "") -> None:
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


# ApexPolygon:
class ApexPolygon(object):
    """Represents a polygon with possible rounded corners."""

    # ApexPolygon.__init__():
    def __init__(
            self,
            points: Tuple[ApexPoint, ...],
            depth: float = 0.0,
            flat: bool = False,
            name: str = ""
    ) -> None:
        """Initialize a ApexPolygon."""
        if not points:
            raise ValueError("bounding box needs at least one point.")  # pragma: no unit cover

        self._bounding_box: ApexBoundBox = ApexBoundBox.from_vectors(points)
        self._depth: float = depth
        self._features: Optional[Tuple[ApexFeature, ...]] = None
        self._flat: bool = flat
        self._name: str = name
        self._points: Tuple[ApexPoint, ...] = points

    # ApexPolygon.bounding_box():
    @property
    def bounding_box(self) -> ApexBoundBox:
        """Return the ApexPolygon ApexBoundBox."""
        return self._bounding_box

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
    def constraints_append(self, drawing: ApexDrawing, constraints: List[Sketcher.Constraint],
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

    # ApexPolygon.flat():
    @property
    def flat(self) -> bool:  # pragma: no unit cover
        """Return the flat flag."""
        return self._flat

    # ApexPolygon.features_get():
    def features_get(self, drawing: ApexDrawing, tracing: str = "") -> Tuple[ApexFeature, ...]:
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

    def forward_transform(self, pose: ApexPose) -> "ApexPolygon":
        """Return a forward transformed ApexPolygon."""
        point: ApexPoint
        points: Tuple[ApexPoint, ...] = tuple([point.forward(pose) for point in self._points])
        return ApexPolygon(points, self._depth, self._flat, self._name)


class ApexCircle(object):
    """Represents a circle."""

    # ApexCircle.__init():
    def __init__(
            self,
            center: ApexPoint,
            depth: float = 0.0,
            flat: bool = False,
            name: str = ""
    ) -> None:
        """Initialize a circle."""
        if center.radius <= 0:
            raise ValueError("ApexCircle has no radius")  # pragma: no unit cover

        x: float = center.x
        y: float = center.y
        radius: float = center.radius
        name = name if name else center.name

        lower: ApexPoint = ApexPoint(x - radius, y - radius, 0.0, name=name, diameter=0.0)
        upper: ApexPoint = ApexPoint(x + radius, y + radius, 0.0, name=name, diameter=0.0)

        self._bounding_box: ApexBoundBox = ApexBoundBox(BoundBox(lower.vector, upper.vector))
        self._circle_feature: Optional[ApexCircleFeature] = None
        self._constraints: Tuple[Sketcher.Constraint, ...] = ()
        self._center: ApexPoint = center
        self._depth: float = depth
        self._flat: bool = flat
        self._name: str = name
        self._radius: float = radius

    # ApexCircleFeature.__repr__():
    def __repr__(self) -> str:
        """Return a string representation of ApexCircle."""
        return (f"ApexCircle({self._center}, "
                f"{self._radius}, '{self._name}')")  # pragma: no unit cover

    # ApexCircle.bounding_box():
    @property
    def bounding_box(self) -> ApexBoundBox:
        """Return the ApexCircle ApexBoundBox."""
        return self._bounding_box

    # ApexCircle.center():
    @property
    def center(self) -> ApexPoint:
        """Return the ApexCircle center ApexPoint."""
        return self._center

    # ApexCircle.circle_feature:
    @property
    def circle_feature(self) -> ApexCircleFeature:
        """Return the ApexCircle ApexCircleFeature."""
        circle_feature: Optional[ApexCircleFeature] = self._circle_feature
        if not circle_feature:
            raise ValueError(f"{self} does not have a feature yet.")  # pragma: no unit cover
        return circle_feature

    # ApexCircle.constraints_append():
    def constraints_append(self, drawing: ApexDrawing, constraints: List[Sketcher.Constraint],
                           tracing: str = "") -> None:
        """Return the ApexCircleFeature constraints."""
        if tracing:
            print("{tracing}=>ApexCircle.constraints_append(*, *): {len(constraints)=}")
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
            print("{tracing}<=ApexCircle.constraints_append(*, *): {len(constraints)=}")

    # ApexCircle.depth():
    @property
    def depth(self) -> float:
        """Return the ApexCircle Depth."""
        return self._depth

    # ApexCircle.flat():
    @property
    def flat(self) -> bool:
        """Return whether the ApexCircle bottom is flat."""
        return self._flat

    # ApexCircle.features_get():
    def features_get(self, drawing: ApexDrawing) -> Tuple[ApexFeature, ...]:
        """Return the ApexCircleFeature."""
        circle_feature: Optional[ApexCircleFeature] = self._circle_feature
        if not circle_feature:
            circle_feature = ApexCircleFeature(drawing, self.center, self.radius, self.name)
            self._circle_feature = circle_feature
        return (circle_feature,)

    # ApexCircle.forward_transform():
    def forward_transform(self, pose: ApexPose) -> "ApexCircle":
        """Return a forward transformed ApexCircle."""
        center: ApexPoint = self.center
        vector: Vector = Vector(center.x, center.y, center.z)
        vector = pose.forward * vector
        new_center: ApexPoint = ApexPoint(vector.x, vector.y, vector.z,
                                          name=center.name, diameter=center.diameter)
        return ApexCircle(new_center, self.depth, self.flat, self.name)

    # ApexCircle.name():
    @property
    def name(self) -> str:
        """Return the name of the ApexCircle."""
        return self._name

    # ApexCircle.radius():
    @property
    def radius(self) -> float:
        """Return the ApexCircle radius."""
        return self._radius


def visibility_set(element: Any, new_value: bool = True) -> None:
    """Set the visibility of an element."""
    # print(f"=>visibility_set({element}, {new_value})")
    if App.GuiUp:   # pragma: no unit cover
        gui_document: Optional[Any] = (
            Gui.ActiveDocument if hasattr(Gui, "ActiveDocument") else None)
        if gui_document and hasattr(gui_document, "Name"):
            name: str = getattr(element, "Name")
            sub_element: Any = gui_document.getObject(name)
            if sub_element is not None and hasattr(sub_element, "Visibility"):
                if isinstance(getattr(sub_element, "Visibility"), bool):
                    setattr(sub_element, "Visibility", new_value)
    # print(f"<=visibility_set({element}, {new_value})")

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


def main() -> int:
    """Run the program."""
    # Open *document_name* and get associated *app_document* and *gui_document*:
    document_name: str = "bar"

    # gui_document: Optional[Gui.Document] = Gui.ActiveDocument if Gui else None

    drawing: ApexDrawing
    center_circle: ApexCircle

    app_document: App.Document = App.newDocument("bar")
    if True:
        # print(f"{app_document=}")
        # import PartDesign
        body: PartDesign.Body = app_document.addObject("PartDesign::Body", "Body")
        datum_plane: Part.ApexFeature = body.newObject("PartDesign::Plane", "DatumPlane")
        xy_plane: App.GeoApexFeature = body.getObject("XY_Plane")
        datum_plane.Support = [(xy_plane, "")]
        datum_plane.MapMode = "FlatFace"
        datum_plane.AttachmentOffset = App.Placement(
            App.Vector(0.0, 0.0, 0.0), App.Rotation(0.0, 0.0, 0.0))
        datum_plane.MapReversed = False
        datum_plane.MapPathParameter = 0.0
        datum_plane.recompute()
        visibility_set(datum_plane)

        # Create the sketch and attach it to the *datum_plane*:
        sketch: Sketcher.SketchObject = body.newObject("Sketcher::SketchObject", "sketch")
        sketch.Support = (datum_plane, "")
        sketch.MapMode = "FlatFace"

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
        box_polygon: ApexPolygon = ApexPolygon(box_points, 0.0, False, "box")

        # Create the *hole_center*:
        center_hole: ApexPoint = ApexPoint(0.0, 0.0, 0.0, name="center_hole", diameter=10.0)
        center_circle = ApexCircle(center_hole, 0.0, False, "center_hole")

        # Create the *drawing*:
        circles: Tuple[ApexCircle, ...] = (center_circle,)
        polygons: Tuple[ApexPolygon, ...] = (box_polygon,)
        drawing = ApexDrawing(circles, polygons, "box_with_hole")

        # Just for fun rotate everything by 60 degrees:
        # rotate30_transform: Transform = Transform(None, None, math.pi / 3.0, None)
        # drawing = drawing.forward_transform(rotate30_transform)

        origin_vector: Vector = drawing.bounding_box.BSW
        drawing_origin: ApexPoint = ApexPoint(origin_vector.x, origin_vector.y, 0.0)
        vector: Vector = Vector(drawing_origin.x, drawing_origin.y, drawing_origin.z)
        reorigin: ApexPose = ApexPose(translate=-vector, name=f"{drawing.name} reorigin")
        drawing = drawing.forward_transform(reorigin)
        drawing.sketch(sketch, drawing_origin, tracing="")

        pad: PartDesign.ApexFeature = body.newObject("PartDesign::Pad", "Pad")
        pad.Profile = sketch
        pad.Length = 10.0
        pad.Reversed = True
        app_document.recompute()

    # Delete previous file *fcstd_path* and then save a new one:
    root: Path = Path("/")
    fcstd_path: Path = root / "tmp" / f"{document_name}.fcstd"
    if fcstd_path.exists():
        fcstd_path.unlink()
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
    main()
