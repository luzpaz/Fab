# FabSolids: Solid: A module for constructing 3D solids.
This module defines the following user facing classes:
* FabSolid: A 3D solid part that corresponds to a STEP file.
* FabMount: A CNC-like work plane on which other operations are performed.

There are internal classes that represent operations such as extrude, pocket, drill, etc.
This internal classes are managed by FabMount methods.

## Table of Contents (alphabetical order):

* 1 Class: [FabMount](#fabsolids--fabmount):
  * 1.1 [get_hash()](#fabsolids----get-hash): Return a has the current contents of a FabMount.
  * 1.2 [record_operation()](#fabsolids----record-operation): Record an operation to a FabMount.
  * 1.3 [set_geometry_group()](#fabsolids----set-geometry-group): Set the FabMount GeometryGroup need for the FabGeometryContex.
  * 1.4 [post_produce1()](#fabsolids----post-produce1): Perform FabMount phase 1 post procduction.
  * 1.5 [to_json()](#fabsolids----to-json): Return FabMount JSON structure.
  * 1.6 [extrude()](#fabsolids----extrude): Perform a extrude operation.
  * 1.7 [pocket()](#fabsolids----pocket): Perform a pocket operation.
  * 1.8 [drill_joins()](#fabsolids----drill-joins): Drill some FabJoin's into a FabMount.
* 2 Class: [FabSolid](#fabsolids--fabsolid):
  * 2.1 [to_json()](#fabsolids----to-json): Return FabProject JSON structure.
  * 2.2 [set_body()](#fabsolids----set-body): Set the BodyBase of a FabSolid.
  * 2.3 [is_solid()](#fabsolids----is-solid):  Return True if FabNode is a FabAssembly.
  * 2.4 [pre_produce()](#fabsolids----pre-produce): Perform FabSolid pre production.
  * 2.5 [get_hash()](#fabsolids----get-hash): Return FabSolid hash.
  * 2.6 [mount()](#fabsolids----mount): Return a new FabMount.
  * 2.7 [drill_joins()](#fabsolids----drill-joins): Apply drill FabJoin holes for a FabSolid.
  * 2.8 [post_produce1()](#fabsolids----post-produce1): Perform FabSolid Phase1 post production.
* 3 Class: [FabStock](#fabsolids--fabstock):
  * 3.1 [enclose()](#fabsolids----enclose): Wrap some stock material around a FabBox.
* 4 Class: [Fab_Extrude](#fabsolids--fab-extrude):
  * 4.1 [get_name()](#fabsolids----get-name): Return Fab_Extrude name.
  * 4.2 [get_kind()](#fabsolids----get-kind): Return Fab_Extrude kind.
  * 4.3 [get_hash()](#fabsolids----get-hash): Return hash for Fab_Extrude operation.
  * 4.4 [post_produce1()](#fabsolids----post-produce1): Produce the Extrude.
  * 4.5 [to_json()](#fabsolids----to-json): Return JSON dictionary for Fab_Extrude.
* 5 Class: [Fab_Hole](#fabsolids--fab-hole):
  * 5.1 [get_name()](#fabsolids----get-name): Return Fab_Hole name.
  * 5.2 [get_kind()](#fabsolids----get-kind): Return Fab_Hole kind.
  * 5.3 [get_hash()](#fabsolids----get-hash): Return Fab_Hole hash.
  * 5.4 [post_produce1()](#fabsolids----post-produce1): Perform Fab_Hole phase 1 post production.
  * 5.5 [to_json()](#fabsolids----to-json): Return the FabHole JSON.
* 6 Class: [Fab_HoleKey](#fabsolids--fab-holekey):
  * 6.1 [get_hash()](#fabsolids----get-hash): Return a hash tuple for a Fab_HoleKey.
* 7 Class: [Fab_Operation](#fabsolids--fab-operation):
  * 7.1 [get_tool_controller()](#fabsolids----get-tool-controller): Return the Fab_Operation tool controller
  * 7.2 [set_tool_controller()](#fabsolids----set-tool-controller): Set the Fab_Operation tool controller and associated index.
  * 7.3 [get_kind()](#fabsolids----get-kind): Return Fab_Operation kind.
  * 7.4 [get_name()](#fabsolids----get-name): Return Fab_Operation name.
  * 7.5 [get_hash()](#fabsolids----get-hash): Return Fab_Operation hash.
  * 7.6 [get_geometries_hash()](#fabsolids----get-geometries-hash): Return hash of FabGeometry's.
  * 7.7 [produce()](#fabsolids----produce): Return the operation sort key.
  * 7.8 [post_produce1()](#fabsolids----post-produce1): NO DOC STRING!
  * 7.9 [to_json()](#fabsolids----to-json): Return a base JSON dictionary for an Fab_Operation.
  * 7.10 [produce_shape_binder()](#fabsolids----produce-shape-binder): Produce the shape binder needed for the extrude, pocket, hole, ... operations.
* 8 Class: [Fab_Pocket](#fabsolids--fab-pocket):
  * 8.1 [Geometry()](#fabsolids----geometry): Return the original Geometry.
  * 8.2 [Depth()](#fabsolids----depth): Return the original Depth.
  * 8.3 [get_hash()](#fabsolids----get-hash): Return Fab_Pocket hash.
  * 8.4 [get_name()](#fabsolids----get-name): Return Fab_Pocket name.
  * 8.5 [get_kind()](#fabsolids----get-kind): Return Fab_Pocket kind.
  * 8.6 [post_produce1()](#fabsolids----post-produce1): Produce the Pocket.
  * 8.7 [to_json()](#fabsolids----to-json): Return JSON dictionary for Fab_Extrude.

## <a name="fabsolids--fabmount"></a>1 Class FabMount:

An operations plane that can be oriented for subsequent machine operations.
This class basically corresponds to a FreeCad Datum Plane.  It is basically the surface
to which the 2D FabGeometry's are mapped onto prior to performing each operation.

Attributes:
* *Name*: (str): The name of the Fab_Plane.
* *Solid*: (FabSolid): The FabSolid to work on.
* *Contact* (Vector): A point on the mount plane.
* *Normal* (Vector): A normal to the mount plane
* *Orient* (Vector):
  A vector that is projected onto the mount plane to specify orientation
  when mounted for CNC operations.
* *Depth* (float): The maximum depth limit for all operations.
* *WorkPlane* (Fab_Query): The CadQuery workplane wrapper class object.

### <a name="fabsolids----get-hash"></a>1.1 `FabMount.`get_hash():

FabMount.get_hash(self) -> Tuple[Any, ...]:

Return a has the current contents of a FabMount.

### <a name="fabsolids----record-operation"></a>1.2 `FabMount.`record_operation():

FabMount.record_operation(self, operation: FabSolids.Fab_Operation) -> None:

Record an operation to a FabMount.

### <a name="fabsolids----set-geometry-group"></a>1.3 `FabMount.`set_geometry_group():

FabMount.set_geometry_group(self, geometry_group: Any) -> None:

Set the FabMount GeometryGroup need for the FabGeometryContex.

### <a name="fabsolids----post-produce1"></a>1.4 `FabMount.`post_produce1():

FabMount.post_produce1(self, produce_state: FabNodes.Fab_ProduceState, tracing: str = '') -> None:

Perform FabMount phase 1 post procduction.

### <a name="fabsolids----to-json"></a>1.5 `FabMount.`to_json():

FabMount.to_json(self) -> Dict[str, Any]:

Return FabMount JSON structure.

### <a name="fabsolids----extrude"></a>1.6 `FabMount.`extrude():

FabMount.extrude(self, name: str, shapes: Union[FabGeometries.FabGeometry, Tuple[FabGeometries.FabGeometry, ...]], depth: float, contour: bool = True, tracing: str = '') -> None:

Perform a extrude operation.

### <a name="fabsolids----pocket"></a>1.7 `FabMount.`pocket():

FabMount.pocket(self, name: str, shapes: Union[FabGeometries.FabGeometry, Tuple[FabGeometries.FabGeometry, ...]], depth: float, tracing: str = '') -> None:

Perform a pocket operation.

### <a name="fabsolids----drill-joins"></a>1.8 `FabMount.`drill_joins():

FabMount.drill_joins(self, joins_name: str, joins: Union[FabJoins.FabJoin, Sequence[FabJoins.FabJoin]], tracing: str = '') -> None:

Drill some FabJoin's into a FabMount.


## <a name="fabsolids--fabsolid"></a>2 Class FabSolid:

Fab: Represents a single 3D solid that is represented as a STEP file.
Inherited Attributes:
* *Name* (str): The model name.
* *Parent* (FabNode): The Parent FabNode.

Attributes:
* *Material* (str): The material to use.
* *Color* (str): The color to use.

### <a name="fabsolids----to-json"></a>2.1 `FabSolid.`to_json():

FabSolid.to_json(self) -> Dict[str, Any]:

Return FabProject JSON structure.

### <a name="fabsolids----set-body"></a>2.2 `FabSolid.`set_body():

FabSolid.set_body(self, body: Any) -> None:

Set the BodyBase of a FabSolid.

### <a name="fabsolids----is-solid"></a>2.3 `FabSolid.`is_solid():

FabSolid.is_solid(self) -> bool:

 Return True if FabNode is a FabAssembly.

### <a name="fabsolids----pre-produce"></a>2.4 `FabSolid.`pre_produce():

FabSolid.pre_produce(self, produce_state: FabNodes.Fab_ProduceState) -> None:

Perform FabSolid pre production.

### <a name="fabsolids----get-hash"></a>2.5 `FabSolid.`get_hash():

FabSolid.get_hash(self) -> Tuple[Any, ...]:

Return FabSolid hash.

### <a name="fabsolids----mount"></a>2.6 `FabSolid.`mount():

FabSolid.mount(self, name: str, contact: cadquery.occ_impl.geom.Vector, normal: cadquery.occ_impl.geom.Vector, orient: cadquery.occ_impl.geom.Vector, depth: float, tracing: str = '') -> FabSolids.FabMount:

Return a new FabMount.

### <a name="fabsolids----drill-joins"></a>2.7 `FabSolid.`drill_joins():

FabSolid.drill_joins(self, name: str, joins: Sequence[FabJoins.FabJoin], mounts: Union[Sequence[FabSolids.FabMount], NoneType] = None) -> None:

Apply drill FabJoin holes for a FabSolid.
Iterate pairwise through a sequence of FabJoin's and FabMount's and for each pair
attempt to drill a bunch the FabJoin holes for the associated FabSolid.  The drill
operation only occurs if the FabJoin is in alignment with the FabMount normal (in
either direction) *and* if the FabJoin intersects with the underlying FabSolid;
otherwise nothing is for that particular FabMount and FabJoin pair.

Arguments:
* *name* (str): The collective name for all of the drills.
* *joins* (Optional[Sequence[FabJoin]]):
  The tuple/list of FabJoin's to apply.
* *mounts* (Optional[Sequence[FabMount]]):
  The mounts to to apply the *joins* to.  If *mounts* is *None*, all of the
  mounts for the current FabSolid are used.  (Default: None)

For now, please call this method after all FabMount's are created.

### <a name="fabsolids----post-produce1"></a>2.8 `FabSolid.`post_produce1():

FabSolid.post_produce1(self, produce_state: FabNodes.Fab_ProduceState, tracing: str = '') -> None:

Perform FabSolid Phase1 post production.


## <a name="fabsolids--fabstock"></a>3 Class FabStock:

Represents the stock matereial for machine a part from.
Attributes:
* *Name* (str): The FabStock Name.
* *StockIncrements* (Vector):
  The increments that the stock cuboid comes in  X, Y, and Z.
  The StockThicknesses attribute will override Z if possible.
* *StockThicknesses* (Tuple[float ...]):
  The standard increments of stock thickness to use.
* *StockMinimumCut* (float):
  The minimum amount that contour operation must remove in X and Y.

### <a name="fabsolids----enclose"></a>3.1 `FabStock.`enclose():

FabStock.enclose(self, box: FabNodes.FabBox) -> Tuple[cadquery.occ_impl.geom.Vector, cadquery.occ_impl.geom.Vector]:

Wrap some stock material around a FabBox.


## <a name="fabsolids--fab-extrude"></a>4 Class Fab_Extrude:

Represents and extrude operation.
Attributes:
* *Name* (str): The operation name.
* *Geometry* (Union[FabGeometry, Tuple[FabGeometry, ...]):
  The FabGeometry (i.e. FabPolygon or FabCircle) or a tuple of FabGeometry's to extrude with.
  When the tuple is used, the largest FabGeometry (which is traditionally the first one)
  is the outside of the extrusion, and the rest are "pockets".  This is useful for tubes.
* *Depth* (float): The depth to extrude to in millimeters.
* *Contour* (bool): If True and profile CNC contour path is performed; otherwise, no profile
  is performed.

### <a name="fabsolids----get-name"></a>4.1 `Fab_Extrude.`get_name():

Fab_Extrude.get_name(self) -> str:

Return Fab_Extrude name.

### <a name="fabsolids----get-kind"></a>4.2 `Fab_Extrude.`get_kind():

Fab_Extrude.get_kind(self) -> str:

Return Fab_Extrude kind.

### <a name="fabsolids----get-hash"></a>4.3 `Fab_Extrude.`get_hash():

Fab_Extrude.get_hash(self) -> Tuple[Any, ...]:

Return hash for Fab_Extrude operation.

### <a name="fabsolids----post-produce1"></a>4.4 `Fab_Extrude.`post_produce1():

Fab_Extrude.post_produce1(self, produce_state: FabNodes.Fab_ProduceState, tracing: str = '') -> None:

Produce the Extrude.

### <a name="fabsolids----to-json"></a>4.5 `Fab_Extrude.`to_json():

Fab_Extrude.to_json(self) -> Dict[str, Any]:

Return JSON dictionary for Fab_Extrude.


## <a name="fabsolids--fab-hole"></a>5 Class Fab_Hole:

FabDrill helper class that represents a hole.

### <a name="fabsolids----get-name"></a>5.1 `Fab_Hole.`get_name():

Fab_Hole.get_name(self) -> str:

Return Fab_Hole name.

### <a name="fabsolids----get-kind"></a>5.2 `Fab_Hole.`get_kind():

Fab_Hole.get_kind(self) -> str:

Return Fab_Hole kind.

### <a name="fabsolids----get-hash"></a>5.3 `Fab_Hole.`get_hash():

Fab_Hole.get_hash(self) -> Tuple[Any, ...]:

Return Fab_Hole hash.

### <a name="fabsolids----post-produce1"></a>5.4 `Fab_Hole.`post_produce1():

Fab_Hole.post_produce1(self, produce_state: FabNodes.Fab_ProduceState, tracing: str = '') -> None:

Perform Fab_Hole phase 1 post production.

### <a name="fabsolids----to-json"></a>5.5 `Fab_Hole.`to_json():

Fab_Hole.to_json(self) -> Dict[str, Any]:

Return the FabHole JSON.


## <a name="fabsolids--fab-holekey"></a>6 Class Fab_HoleKey:

Represents a group of holes that can be grouped together.
Attributes:
* *ThreadName* (str): The name of the thread class for the hole.
* *Kind* (str): The kind of thread hole (one of "thread", "close", or "standard".)
* *Depth* (float): The hole depth.
* *IsTop* (bool): True when hole is the top of the fastener for countersink and counterboring.

### <a name="fabsolids----get-hash"></a>6.1 `Fab_HoleKey.`get_hash():

Fab_HoleKey.get_hash(self) -> Tuple[Any, ...]:

Return a hash tuple for a Fab_HoleKey.


## <a name="fabsolids--fab-operation"></a>7 Class Fab_Operation:

An base class for FabMount operations -- Fab_Extrude, Fab_Pocket, FabHole, etc.
Attributes:
* *Mount* (FabMount):
  The FabMount to use for performing operations.
* *ToolController* (Optional[FabToolController]):
  The tool controller (i.e. speeds, feeds, etc.) to use. (Default: None)
* *ToolControllerIndex* (int):
  The tool controller index associated with the tool controller.  (Default: -1)
* *JsonEnabled* (bool):
  Enables the generation of JSON if True, otherwise suppresses it.  (Default: True)
* *Active* (bool):
  If True, the resulting operation is performed.  About the only time this is set to False
  is for an extrude of stock material like a C channel, I beam, etc.  (Default: True)

### <a name="fabsolids----get-tool-controller"></a>7.1 `Fab_Operation.`get_tool_controller():

Fab_Operation.get_tool_controller(self) -> FabUtilities.FabToolController:

Return the Fab_Operation tool controller

### <a name="fabsolids----set-tool-controller"></a>7.2 `Fab_Operation.`set_tool_controller():

Fab_Operation.set_tool_controller(self, tool_controller: FabUtilities.FabToolController, tool_controllers_table: Dict[FabUtilities.FabToolController, int]) -> None:

Set the Fab_Operation tool controller and associated index.

### <a name="fabsolids----get-kind"></a>7.3 `Fab_Operation.`get_kind():

Fab_Operation.get_kind(self) -> str:

Return Fab_Operation kind.

### <a name="fabsolids----get-name"></a>7.4 `Fab_Operation.`get_name():

Fab_Operation.get_name(self) -> str:

Return Fab_Operation name.

### <a name="fabsolids----get-hash"></a>7.5 `Fab_Operation.`get_hash():

Fab_Operation.get_hash(self) -> Tuple[Any, ...]:

Return Fab_Operation hash.

### <a name="fabsolids----get-geometries-hash"></a>7.6 `Fab_Operation.`get_geometries_hash():

Fab_Operation.get_geometries_hash(self, geometries: Union[FabGeometries.FabGeometry, Tuple[FabGeometries.FabGeometry, ...]]) -> Tuple[Any, ...]:

Return hash of FabGeometry's.

### <a name="fabsolids----produce"></a>7.7 `Fab_Operation.`produce():

Fab_Operation.produce(self, tracing: str = '') -> Tuple[str, ...]:

Return the operation sort key.

### <a name="fabsolids----post-produce1"></a>7.8 `Fab_Operation.`post_produce1():

Fab_Operation.post_produce1(self, produce_state: FabNodes.Fab_ProduceState, tracing: str = '') -> None:

NO DOC STRING!

### <a name="fabsolids----to-json"></a>7.9 `Fab_Operation.`to_json():

Fab_Operation.to_json(self) -> Dict[str, Any]:

Return a base JSON dictionary for an Fab_Operation.

### <a name="fabsolids----produce-shape-binder"></a>7.10 `Fab_Operation.`produce_shape_binder():

Fab_Operation.produce_shape_binder(self, part_geometries: Tuple[Any, ...], prefix: str, tracing: str = '') -> Any:

Produce the shape binder needed for the extrude, pocket, hole, ... operations.


## <a name="fabsolids--fab-pocket"></a>8 Class Fab_Pocket:

Represents a pocketing operation.
Attributes:
* *Name* (str): The operation name.
* *Geometry* (Union[FabGeometry, Tuple[FabGeometry, ...]]):
   The Polygon or Circle to pocket.  If a tuple is given, the smaller FabGeometry's
   specify "islands" to not pocket.
* *Depth* (float): The pocket depth in millimeters.
* *Bottom_Path* (str): The the path to the generated Pocket bottom STEP file.

### <a name="fabsolids----geometry"></a>8.1 `Fab_Pocket.`Geometry():

Fab_Pocket.Geometry(self) -> Union[FabGeometries.FabGeometry, Tuple[FabGeometries.FabGeometry, ...]]:

Return the original Geometry.

### <a name="fabsolids----depth"></a>8.2 `Fab_Pocket.`Depth():

Fab_Pocket.Depth(self) -> float:

Return the original Depth.

### <a name="fabsolids----get-hash"></a>8.3 `Fab_Pocket.`get_hash():

Fab_Pocket.get_hash(self) -> Tuple[Any, ...]:

Return Fab_Pocket hash.

### <a name="fabsolids----get-name"></a>8.4 `Fab_Pocket.`get_name():

Fab_Pocket.get_name(self) -> str:

Return Fab_Pocket name.

### <a name="fabsolids----get-kind"></a>8.5 `Fab_Pocket.`get_kind():

Fab_Pocket.get_kind(self) -> str:

Return Fab_Pocket kind.

### <a name="fabsolids----post-produce1"></a>8.6 `Fab_Pocket.`post_produce1():

Fab_Pocket.post_produce1(self, produce_state: FabNodes.Fab_ProduceState, tracing: str = '') -> None:

Produce the Pocket.

### <a name="fabsolids----to-json"></a>8.7 `Fab_Pocket.`to_json():

Fab_Pocket.to_json(self) -> Dict[str, Any]:

Return JSON dictionary for Fab_Extrude.



