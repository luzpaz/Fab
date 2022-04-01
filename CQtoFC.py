#!/usr/bin/env python3
"""CQtoFC: A module for reading CadQuery generated STEP files into FreeCAD.

This shell script converts the JSON file (.json) and associated STEP (.stp) files generated by
Fab Project into FreeCAD document files (.FCStd) and optionally it can generate CNC G code (.nc)
files.

This program is meant to be run by the FreeCAD Python interpreter.  Since there is no easy
way to pass command line arguments the interpreter, there is a shell file called `cq2fc.sh`
sets everything up to run in FreeCAD.  It passes arguments/optons in via Environment variables.
(Crude, but effective.)

The environment variable that are read are:

JSON: This the path to the JSON file.
CNC: If this is present, CNC G code (.nc) files are generated.

"""

# <--------------------------------------- 100 characters ---------------------------------------> #

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import sys
from typing import Any, cast, List, Dict, IO, Optional, Tuple

from PathScripts import PathJob, PathProfile, PathPostProcessor, PathUtil  # type: ignore
_ = PathJob  # TODO: Remove
_ = PathProfile  # TODO: Remove
_ = PathPostProcessor  # TODO: Remove
_ = PathUtil  # TODO: Remove

# This causes out flake8 to think App are defined.
# It is actually present in the FreeCAD Python exectution envriorment.
if False:
    App = None

# Freecad has two different importers depending upon whether it is GUI mode or not.
from FreeCAD import Vector  # type: ignore
if App.GuiUp:  # type: ignore
    import FreeCADGui as Gui  # type: ignore
    from FreeCAD import ImportGui as FCImport  # type: ignore
    from PathScripts import PathJobGui  # type: ignore
    _ = PathJobGui  # TODO: Remove
else:
    from FreeCAD import Import as FCImport  # type: ignore


# FabCQtoFC:
@dataclass
class FabCQtoFC(object):
    """FabCQtoFC: Import CadQuery .step files into FreeCAD."""

    JsonPath: Path
    ToolsPath: Optional[Path]
    StepsDocument: Any = field(init=False, repr=False)
    ProjectDocument: Any = field(init=False, repr=False)
    AllDocuments: List[Any] = field(init=False, repr=False)
    PendingLinks: List[Tuple[Any, Any]] = field(init=False, repr=False)
    CurrentPart: Any = None
    CurrentLink: Any = None
    CurrentJob: Any = None
    CurrentGroup: Any = None
    CurrentNormal: Any = None

    # FabCQtoFC.__post_init__():
    def __post_init__(self) -> None:
        """Initialize FabCQtoFC."""
        assert isinstance(self.JsonPath, Path), self.JsonPath
        self.StepsDocument = None
        self.AllDocuments = []
        self.PendingLinks = []
        self.PendingLinks: List[Tuple[Any, Any]] = []
        self.ProjectDocument = None
        self.CurrentNormal = None

    # FabCQtoFC.process():
    def process(self, indent: str = "", tracing: str = "") -> None:
        """Process a JSON file into a FreeCAD documents."""
        next_tracing: str = tracing + "  " if tracing else ""
        if tracing:
            print(f"{tracing}=>FabCQtFC.process({str(self.JsonPath), {self.ToolsPath}})")

        # Create the *steps_document*:
        json_directory: Path = self.JsonPath.parent
        steps_document: Any = App.newDocument("Step_Files")  # type: ignore
        self.StepsDocument = steps_document
        self.AllDocuments.append(steps_document)

        # Read in *json_path*:
        json_file: IO[str]
        json_text: str = ""
        if self.JsonPath.suffix != ".json":
            raise RuntimeError(f"JSON file must have `.json` suffix: '{str(self.JsonPath)}'")
        if tracing:
            print(f"{tracing}Loading {str(self.JsonPath)}")
        with open(self.JsonPath, "r") as json_file:
            json_text = json_file.read()
        if tracing:
            print(f"{tracing}Parsing {str(self.JsonPath)}")
        json_root = cast(Dict[str, Any], json.loads(json_text))
        assert isinstance(json_root, dict), json_root

        # Recursively walk the tree starting at *json_root*:
        if tracing:
            print(f"{tracing}Processing {str(self.JsonPath)}")
        self.node_process(("Root",), json_root, indent=indent, tracing=next_tracing)

        # Save *all_documents*:
        document: Any
        for document in self.AllDocuments:
            save_path: Path = json_directory / f"{document.Label}.FCStd"
            if save_path.exists():
                save_path.unlink()
            document.recompute()
            document.saveAs(str(save_path))

        # Install all of the *pending_links*:
        pending_link: Tuple[Any, Any]
        link: Any
        part: Any
        for link, part in self.PendingLinks:
            link.setLink(part)
        if tracing:
            print(f"{tracing}<=FabCQtFC.process({str(self.JsonPath), {self.ToolsPath}})")

    # FabCQtoFC.type_verify():
    def type_verify(self, value: Any, value_type: type,
                    tree_path: Tuple[str, ...], tag: str) -> None:
        """Verify JSON type."""
        if not isinstance(value, value_type):
            message: str = f"{tree_path}: {tag}: Got {type(value)}, not {value_type}"
            print(message)
            assert False, message

    # FabCQtoFC.key_verify():
    def key_verify(self, key: str, table: Dict[str, Any], key_type: type,
                   tree_path: Tuple[str, ...], tag: str) -> Any:
        """Verify key is in dictionary and has correct type."""
        if key not in table:
            message: str = f"{tree_path}: {tag}: '{key}' is not one of {tuple(table.keys())}'"
            print(message)
            assert False, message
        value: Any = table[key]
        self.type_verify(value, key_type, tree_path, tag)
        return value

    # FabCQtoFC.node_process():
    def node_process(self, tree_path: Tuple[str, ...], json_dict: Dict[str, Any],
                     indent: str = "", tracing: str = "") -> None:
        """Process one 'node' of JSON content."""

        # Set up *tracing* and pretty print *indent*:
        next_tracing: str = tracing + "  " if tracing else ""
        next_indent = indent + "  " if indent else ""
        if tracing:
            print(f"{tracing}=>FabCQtoFC.child_process(*, {tree_path}, '{indent}')")
            print(f"{tracing}{json_dict=}")

        # Do some sanity checking:
        error_message: str
        self.type_verify(json_dict, dict, tree_path, "json_dict")
        kind = cast(str, self.key_verify("Kind", json_dict, str, tree_path, "Kind"))
        label = cast(str, self.key_verify("Label", json_dict, str, tree_path, "Label"))
        if indent:
            print(f"{indent}{label}:")
            print(f"{indent} Kind: {kind}")

        # Verify that that *kind* is one of the *allowed_kinds*:
        allowed_kinds: Tuple[str, ...] = (
            "Project", "Document", "Assembly", "Solid", "Mount",
            "Extrude", "Pocket", "Drill")
        if kind not in allowed_kinds:
            error_message = f"{tree_path}: Node kind '{kind}' not one of {allowed_kinds}"
            print(error_message)
            assert False, error_message

        job: Any = None
        normal: Any = None

        # Dispatch on *kind*:
        if kind == "Project":
            pass
        elif kind == "Document":
            self.process_document(json_dict, label, indent, tree_path, tracing=next_tracing)
        elif kind == "Assembly":
            self.process_assembly(json_dict, label, indent, tree_path, tracing=next_tracing)
        elif kind == "Solid":
            self.process_solid(json_dict, label, indent, tree_path, tracing=next_tracing)
        elif kind == "Mount":
            self.process_mount(json_dict, label, indent, tree_path, tracing=next_tracing)
        elif kind == "Extrude":
            contour = cast(bool, self.key_verify("_Contour", json_dict, bool, tree_path,
                                                 "Extrude._Contour"))
            depth = cast(float, self.key_verify("_Depth", json_dict, float, tree_path,
                                                "Extrude._Depth"))
            final_depth = cast(float, self.key_verify("_FinalDepth", json_dict, float, tree_path,
                                                      "Extrude._FinalDepth"))
            step_down = cast(float, self. key_verify("_StepDown", json_dict, float, tree_path,
                                                     "Extrude._StepDown"))
            step_file = cast(str, self.key_verify("_StepFile", json_dict, str, tree_path,
                                                  "Extrude._StepFile"))
            start_depth = cast(float, self.key_verify("_StartDepth", json_dict, float, tree_path,
                                                      "Extrude._StartDepth"))
            if indent:
                print(f"{indent} _Contour: {bool}")
                print(f"{indent} _Depth: {depth}")
                print(f"{indent} _FinalDepth: {final_depth}")
                print(f"{indent} _StartDepth: {start_depth}")
                print(f"{indent} _StepDown: {step_down}")
                print(f"{indent} _StepFile: {step_file}")

            def top_faces(obj: Any, normal: Vector, tracing: str = "") -> List[str]:
                """Return top faces."""
                if tracing:
                    print(f"{tracing}=>top_faces({obj}, {normal})")
                assert hasattr(obj, "Shape")
                shape = obj.Shape
                top_face_names: List[str] = []
                face_index: int
                epsilon: float = 1.0e-8
                for face_index in range(len(shape.Faces)):
                    face_name: str = f"Face{face_index+1}"
                    face: Any = shape.getElement(face_name)
                    # if face.Surface.Axis == Vector(0, 0, 1) and face.Orientation == 'Forward':
                    normal_error: float = abs((face.Surface.Axis - normal).Length)
                    if normal_error < epsilon and face.Orientation == 'Forward':
                        top_face_names.append(face_name)
                if tracing:
                    print(f"{tracing}<=top_faces({obj}, {normal})=>{top_face_names}")
                return top_face_names

            def do_contour(obj: Any, name: str, job: Any, normal: Vector,
                           start_depth: float, step: float, final_depth: float,
                           tracing: str = "") -> Any:
                """Create an exterior contour."""
                next_tracing: str = tracing + " " if tracing else ""
                if tracing:
                    print(f"{tracing}=>contour({obj=}, {name=}, {job=}, {normal=})")
                top_face_names: List[str] = top_faces(obj, normal, tracing=next_tracing)
                if top_face_names:
                    profile = PathProfile.Create(name)
                    profile.Base = (obj, top_face_names[0])
                    profile.setExpression('StepDown', None)
                    profile.StepDown = step_down
                    profile.setExpression('StartDepth', None)
                    profile.StartDepth = start_depth
                    profile.setExpression('FinalDepth', None)
                    profile.FinalDepth = final_depth
                    profile.processHoles = False
                    profile.processPerimeter = True

                    profile.recompute()
                if tracing:
                    print(f"{tracing}<=contour()=>{profile}")
                return profile

            job = self.CurrentJob
            normal = self.CurrentNormal
            assert job is not None, "No job present"

            if contour:
                profile: Any = do_contour(self.CurrentPart, f"{job.Label}_profile", job, normal,
                                          start_depth, step_down, final_depth, tracing=indent)
                _ = profile

        elif kind == "Pocket":
            depth = cast(float,
                         self.key_verify("_Depth", json_dict, float, tree_path, "Extrude._Depth"))
            step_file = cast(str,
                             self.key_verify("_Step", json_dict, str, tree_path, "Pocket._Step"))
            if indent:
                print(f"{indent} _Depth: {depth}")
                print(f"{indent} _Step: {step_file}")
        else:
            message = f"{kind} not one of {allowed_kinds}"
            print(message)
            assert False, message

        if "children" in json_dict:
            children = cast(List[Dict[str, Any]],
                            self.key_verify("children", json_dict, list, tree_path, "Children"))
            if indent:
                print(f"{indent} children ({len(children)}):")

            child_dict: Dict[str, Any]
            for child_dict in children:
                self.type_verify(child_dict, dict, tree_path, "Child")
                child_name = cast(str,
                                  self.key_verify("Label", child_dict, str, tree_path, "Label"))
                child_tree_path: Tuple[str, ...] = tree_path + (child_name,)
                self.node_process(child_tree_path, child_dict,
                                  indent=next_indent, tracing=next_tracing)
        if tracing:
            print(f"{tracing}<=FabCQtoFC.child_process({tree_path}, '{indent}')")

    # FabCQtoFC.process_assembly():
    def process_assembly(self, json_dict: Dict[str, Any], label: str,
                         indent: str, tree_path: Tuple[str, ...], tracing: str = "") -> None:
        if tracing:
            print(f"{tracing}=>FabCQtoFC.process_assembly(*, '{label}', {tree_path})")
        if self.CurrentGroup:
            self.CurrentGroup = self.CurrentGroup.newObject("App::DocumentObjectGroup", label)
        else:
            self.CurrentGroup = self.ProjectDocument.addObject("App::DocumentObjectGroup", label)
        if tracing:
            print(f"{tracing}<=FabCQtoFC.process_assembly(*, '{label}', {tree_path})")

    # FabCQtoFC.process_document():
    def process_document(self, json_dict: Dict[str, Any], label: str,
                         indent: str, tree_path: Tuple[str, ...], tracing: str = "") -> None:
        """Process a Document JSON node."""
        if tracing:
            print(f"{tracing}=>FabCQtoFC.process_document(*, '{label}', {tree_path})")
        file_path: str = cast(str, self.key_verify(
            "_FilePath", json_dict, str, tree_path, "Document._File_Path"))
        project_document = App.newDocument(label)  # type: ignore
        project_document.Label = label
        if indent:
            print(f"{indent} _FilePath: {file_path}")
            self.ProjectDocument = project_document
            self.AllDocuments.append(project_document)
        if tracing:
            print(f"{tracing}<=FabCQtoFC.process_document(*, '{label}', {tree_path})")

    # FabCQtoFC.process_mount():
    def process_mount(self, json_dict: Dict[str, Any], label: str,
                      indent: str, tree_path: Tuple[str, ...], tracing: str = "") -> None:
        """Process a Mount JSON node."""

        if tracing:
            print(f"{tracing}=>FabCQtotFC.process_mount(*, {label}, {tree_path})")
        contact_list: List[float] = cast(
            list, self.key_verify("_Contact", json_dict, list, tree_path, "Solid._Contact"))
        normal_list: List[float] = cast(
            list, self.key_verify("_Normal", json_dict, list, tree_path, "Solid._Normal"))
        orient_list: List[float] = cast(
            list, self.key_verify("_Orient", json_dict, list, tree_path, "Solid._Orient"))
        contact: Vector = Vector(contact_list)
        normal = Vector(normal_list)
        orient: Vector = Vector(orient_list)
        if indent:
            print(f"{indent} _Contact: {contact}")
            print(f"{indent} _Normal: {normal}")
            print(f"{indent} _Orient: {orient}")

        job = PathJob.Create('Job', [self.CurrentPart], None)
        job_name: str = f"{self.CurrentPart.Label}_{label}"
        gcode_path: str = f"/tmp/{job_name}.ngc"
        job.PostProcessorOutputFile = gcode_path
        job.PostProcessor = 'grbl'
        job.PostProcessorArgs = '--no-show-editor'
        job.Label = job_name
        self.CurrentJob = job
        self.CurrentNormal = normal

        if App.GuiUp:  # type: ignore
            proxy: Any = PathJobGui.ViewProvider(job.ViewObject)
            # The statement below causes a bunch of rearrangement of the FreeCAD
            # object tree to push all off the Path related object to be under the
            # FreeCAD Path Job object.  This is really nice because it provides
            # the ability toggle the path trace visibility in one place.  The lovely
            # line below triggers a call to  PathJob.ObjectJob.__set__state__() method.
            # Which appears to do the rearrangement.  Unfortunately, this rearrangement
            # does not occur in embedded mode, so the resulting object trees look
            # quite different.  This is the FreeCAD way.
            job.ViewObject.Proxy = proxy  # This assignment rearranges the Job.

        if tracing:
            print(f"{tracing}<=FabCQtotFC.process_mount(*, {label}, {tree_path})")

    # CQtoFC.process_solid():
    def process_solid(self, json_dict: Dict[str, Any], label: str,
                      indent: str, tree_path: Tuple[str, ...], tracing: str = "") -> None:
        """Process a Solid JSON node."""
        if tracing:
            print(f"{tracing}=>FabCQtotFC.process_solid(*, {label}, {tree_path})")

        step_file: str = cast(str, self.key_verify("_Step",
                                                   json_dict, str, tree_path, "Solid._step"))
        if indent:
            print(f"{indent} _Step: {step_file}")

        # This code currently trys to work with object in a seperate *steps_document* and
        # the main *project_document*.  Change the conditional to switch between.
        use_project_document: bool = True
        document: Any = self.ProjectDocument if use_project_document else self.StepsDocument
        before_size: int = len(document.RootObjects)
        FCImport.insert(step_file, document.Label)
        after_size: int = len(document.RootObjects)
        assert before_size + 1 == after_size, (before_size, after_size)
        part: Any = document.getObject(label)
        part.Label = f"{label}_Step"
        step_object: Any = document.RootObjects[before_size]
        step_object.Label = label

        # When the STEP files are colocated with the assemblies and such, the visibiliy
        # of the associated *gui_step_object* needs to be disabled.
        if use_project_document and App.GuiUp:  # type: ignore
            gui_document: Any = Gui.getDocument(document.Label)  # type: ignore
            gui_step_object: Any = gui_document.getObject(label)
            gui_step_object.Visibility = False

        # Install *link* into *group*.  Complete the link later on using *pending_links*:
        link: Any = self.CurrentGroup.newObject("App::Link", label)
        self.PendingLinks.append((link, part))

        self.CurrentPart = part
        self.CurrentLink = link
        self.CurrentJob = None
        self.CurrentNormal = None

        if tracing:
            print(f"{tracing}<=FabCQtotFC.process_solid(*, {label}, {tree_path})")


# main():
def main() -> None:
    """The main program."""
    environ = cast(Dict[str, str], os.environ)
    json_file_name: str = environ["JSON"] if "JSON" in environ else "/tmp/TestProject.json"
    cnc: bool = "CNC" in environ
    tools_path: Optional[Path] = Path(".") / "Tools" if cnc else None
    json_reader: FabCQtoFC = FabCQtoFC(Path(json_file_name), tools_path)
    json_reader.process(indent="  ", tracing="")
    if not App.GuiUp:  # type: ignore
        sys.exit()


if __name__ == "__main__":
    main()
