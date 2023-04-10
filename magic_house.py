import bpy
import math
import random
from typing import Tuple 

bl_info = {
    "name": "Magic Builder",
    "author": "Bedir Tapkan",
    "version": (1, 2),
    "blender": (3, 50, 0),
    "location": "View3D > Sidebar > MagicBuilder",
    "description": "Generates a procedural building with custom dimensions and design blocks.",
    "warning": "You need to have the meshes assuming a same size box surrounding them for a proper custom result.",
    "category": "Object",
}

# Add subcollections for the different parts
type_names = {
    'gound_level': ['bottom_edge', 'bottom_corner', 'bottom_center'],
    'middle_level': ['middle_edge', 'middle_corner', 'middle_center'],
    'roof_level': ['roof_edge', 'roof_corner', 'roof_center']
}

    
class MB_OT_MagicBuilder(bpy.types.Operator):
    '''
    Generates a house with the given design blocks.
    '''
    bl_idname = "mb.generate_building"
    bl_label = "Magic Builder"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.building_setup(
            max_x=context.scene.mb_max_x,
            max_y=context.scene.mb_max_y,
            max_z=context.scene.mb_max_z,
            start_degree=context.scene.mb_start_degree,
            start_loc=context.scene.mb_start_loc,
            add_roof=context.scene.mb_add_roof,
            collection_name=context.scene.mb_collection_name,
            design_collection_name=context.scene.mb_design_collection_name,
            extra_probability=context.scene.mb_extra_probability,
        )

        if self.design_collection is None:
            self.report({'ERROR'}, f"Collection {context.scene.mb_design_collection_name} not found")
            return {'CANCELLED'}
        self.set_piece_types()

        self.generate_building()

        return {'FINISHED'}

    def building_setup(self,  max_x: int, 
                            max_y: int, 
                            max_z: int, 
                            start_degree: Tuple[float], 
                            start_loc: Tuple[float], 
                            add_roof: bool, 
                            collection_name: str, 
                            design_collection_name: str,
                            extra_probability: float = 0.4,): 
        self.add_roof = add_roof
        self.start_degree = start_degree
        self.start_loc = start_loc
        self.max_x = max_x
        self.max_y = max_y
        self.max_z = max_z
        self.collection_name = collection_name
        self.piece_size = self.find_piece_size()
        self.extra_probability = extra_probability

        # Get the design collection
        self.design_collection = bpy.data.collections.get(design_collection_name)
        self.clear_collection()

    def clear_collection(self):
        if self.collection_name in bpy.data.collections:
            old_collection = bpy.data.collections[self.collection_name]
            for obj in old_collection.objects:
                old_collection.objects.unlink(obj)
                bpy.data.objects.remove(obj)
            bpy.data.collections.remove(old_collection)

            # Purge orphaned data
            bpy.ops.outliner.orphans_purge() # purge collections
            bpy.ops.outliner.orphans_purge() # purge objects
            bpy.ops.outliner.orphans_purge() # purge meshes

    def is_corner(self, coordinates: Tuple[int]) -> bool:
        '''Returns true if coordinates indicate a corner location.'''
        return coordinates[0] in [0, self.max_x-1] and coordinates[1] in [0, self.max_y-1]

    def is_inside(self, coordinates: Tuple[int]) -> bool:
        '''Returns true if coordinates indicate a location that is not an edge.'''
        return coordinates[0] < self.max_x-1 and coordinates[0] > 0 and coordinates[1] > 0 and coordinates[1] < self.max_y-1

    def find_piece_size(self):
        # !@
        # Get piece dimensions
        # piece_size = piece.dimensions
        return (2., 2., 2.)

    def set_piece_type(self, piece_type: str):
        '''
        Searches for a piece with the given name in the design collection
        '''
        pieces = {}
        # Search for all the objects in the 
        nested_collections = self.design_collection.children_recursive
        nested_collections = {c.name: c for c in nested_collections}
        collection = None
        if piece_type in nested_collections:
            collection = nested_collections.get(piece_type)
        if not collection:
            self.report({'ERROR'}, f'No collection found with name {piece_type}. You must have\n' +\
                'a collection with the name of the piece type and the objects inside it.')
            return None
        # get the pieces from the collection
        if collection.objects:
            for obj in collection.objects:
                piece_sep = obj.name.split('_')
                if len(piece_sep) > 1 and piece_sep[0] in ['prop', 'extra']:
                    if piece_sep[1] not in pieces:
                        pieces[piece_sep[1]] = {'prop': None, 'extra': []}
                    if piece_sep[0] == 'prop' and pieces[piece_sep[1]]['prop'] is not None:
                        self.report({'ERROR'}, f'Only one prop object is allowed for each id. {piece_sep[1]} has more than one prop object.')
                        return None
                    if piece_sep[0] == 'prop':
                        pieces[piece_sep[1]]['prop'] = obj
                    else:
                        pieces[piece_sep[1]]['extra'].append(obj)
                # we ignore the objects that are not part of the design
        else:
            self.report({'ERROR'}, f'No piece found for {piece_type}. You must have\n' +\
                'a collection with the name of the piece type and the objects inside it starting with prop_ or extra_.')
            return None
        return pieces

    def set_piece_types(self):
        self.piece_types = {}
        for piece_types in type_names.values():
            for piece_type in piece_types:
                self.piece_types[piece_type] = self.set_piece_type(piece_type)

    def get_piece(self, piece_type):
        '''Randomly selects a prop piece from the given type'''
        if not self.piece_types[piece_type]:
            return None, None
        idx = random.choice(list(self.piece_types[piece_type].keys()))
        return self.piece_types[piece_type][idx]['prop'], idx

    def get_extras(self, piece_type, piece_idx):
        '''Randomly selects extra pieces from the given type unlike prop selection
        which allows only a single piece to be selected. Extras are optional and multiple
        extras can be selected all at once.'''
        extras = []
        if self.piece_types[piece_type][piece_idx]['extra']:
            for extra in self.piece_types[piece_type][piece_idx]['extra']:
                if random.random() < self.extra_probability:
                    extras.append(extra)
        return extras

    def set_piece_rotation(self, piece, rotation_degrees: Tuple[float]):
        '''Handle rotating the objects'''
        piece.rotation_euler = (math.radians(rotation_degrees[0]),
                                math.radians(rotation_degrees[1]),
                                math.radians(rotation_degrees[2]))
    
    def get_piece_rotation(self, coordinates: Tuple[int], piece_type: str):
        if piece_type == 'roof_edge':
            if coordinates[0] == 0:
                return (0, 0, 270)
            elif coordinates[0] == self.max_x - 1:
                return (0, 0, 90)
            elif coordinates[1] == self.max_y - 1:
                return (0, 0, 180)
            else:
                return (0, 0, 0)
        elif piece_type == 'roof_corner':
            if coordinates[0] == 0 and coordinates[1] == 0:
                return (0, 0, 0)
            elif coordinates[0] == self.max_x - 1 and coordinates[1] == 0:
                return (0, 0, 90)
            elif coordinates[0] == self.max_x - 1 and coordinates[1] == self.max_y - 1:
                return (0, 0, 180)
            else:
                return (0, 0, 270)
        elif piece_type == 'roof_center':
            if coordinates[0] == 0 and coordinates[1] == 0:
                return (0, 0, 0)
            elif coordinates[0] == self.max_x - 1 and coordinates[1] == 0:
                return (0, 0, 90)
            elif coordinates[0] == self.max_x - 1 and coordinates[1] == self.max_y - 1:
                return (0, 0, 180)
            else:
                return (0, 0, 270)
        elif piece_type.endswith('corner'):
            if coordinates[0] == 0 and coordinates[1] == 0:
                return (0, 0, 180)
            elif coordinates[0] == self.max_x - 1 and coordinates[1] == 0:
                return (0, 0, 270)
            elif coordinates[0] == self.max_x - 1 and coordinates[1] == self.max_y - 1:
                return (0, 0, 0)
            else:
                return (0, 0, 90)
        elif piece_type.endswith('edge'):
            if coordinates[0] == 0:
                return (0, 0, 90)
            elif coordinates[0] == self.max_x - 1:
                return (0, 0, 270)
            elif coordinates[1] == self.max_y - 1:
                return (0, 0, 0)
            else:
                return (0, 0, 180)
        else: # center
            return (0, 0, 0)

    def duplicate_objects_with_children(self, obj, target_collection, addon_prefs):
        duplicate = obj.copy()
        duplicate.data = obj.data.copy()  # Create a copy of the object's data (e.g., mesh data)
        target_collection.objects.link(duplicate)

        for child in obj.children:
            # if the child is hidden, we need to unhide it to duplicate it
            if child.hide_get():
                child.hide_set(False)

                child_duplicate = self.duplicate_objects_with_children(child, target_collection, addon_prefs)
                child_duplicate.parent = duplicate

                child.hide_set(True)
                child_duplicate.hide_set(True)
            else:
                child_duplicate = self.duplicate_objects_with_children(child, target_collection, addon_prefs)
                child_duplicate.parent = duplicate

            # Apply the child object's transformation relative to the parent
            child_duplicate.matrix_parent_inverse = child.matrix_parent_inverse.copy()

            # Update the boolean modifier if necessary
            for mod in duplicate.modifiers:
                if mod.type == 'BOOLEAN' and mod.object == child:
                    mod.object = child_duplicate

        return duplicate

    def generate_building(self): 
        self.collection = bpy.data.collections.new(self.collection_name) 

        # Link to the context
        bpy.context.scene.collection.children.link(self.collection)

        z_lim = (self.max_z + 1) if self.add_roof else self.max_z
        
        for i in range(self.max_y * self.max_x * z_lim):
            coordinates = i % self.max_x, (i // self.max_x) % self.max_y, i // (self.max_x * self.max_y)
            
            # Create floor collection if it doesn't exist
            floor_collection_name = f'floor_{coordinates[2]}'
            if floor_collection_name not in bpy.data.collections:
                floor_collection = bpy.data.collections.new(floor_collection_name)
                floor_collection.color_tag = 'COLOR_0' + str(coordinates[2] % 8 + 1)
                self.collection.children.link(floor_collection)
            else:
                floor_collection = bpy.data.collections.get(floor_collection_name)

            # Pick the suitable piece
            if self.is_inside(coordinates):
                if (self.add_roof and coordinates[2] < self.max_z) or coordinates[2] == self.max_z - 1:
                    continue
                piece_type = 'center'
            else:
                piece_type = 'corner' if self.is_corner(coordinates) else 'edge'

            if coordinates[2] == 0:
                piece_type = 'bottom_' + piece_type
            elif coordinates[2] == self.max_z:
                piece_type = 'roof_' + piece_type
            else:
                piece_type = 'middle_' + piece_type
            
            piece_orig, idx = self.get_piece(piece_type)
            if piece_orig is None:
                continue
            addon_prefs = bpy.context.preferences.addons[__name__].preferences
            piece = self.duplicate_objects_with_children(piece_orig, floor_collection, addon_prefs)
            piece.location = (
                self.start_loc[0] + coordinates[0] * self.piece_size[0],
                self.start_loc[1] + coordinates[1] * self.piece_size[1],
                self.start_loc[2] + coordinates[2] * self.piece_size[2]
            )
            piece_rotation = self.get_piece_rotation(coordinates, piece_type)
            self.set_piece_rotation(piece, piece_rotation)

            # Add extras
            extras = self.get_extras(piece_type, idx)
            for extra_orig in extras:
                extra = self.duplicate_objects_with_children(extra_orig, floor_collection, addon_prefs)
                extra.location = piece.location
                self.set_piece_rotation(extra, piece_rotation)



class MB_OT_BuildingTemplateCreator(bpy.types.Operator):
    bl_idname = "mb.building_template_creator"
    bl_label = "Create Building Template"
    bl_description = "Creates a template for the building design objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    def create_design_collection_template(self):
        '''
        Creates a collection template for the design
        '''
        # Create the collection
        collection = bpy.data.collections.new("MB_Design_System")
        collection.color_tag = 'COLOR_06'
        # Link to the context
        bpy.context.scene.collection.children.link(collection)

        # Create the subcollections
        idx_p = 0
        first_item = True
        for parent_name, sub_names in type_names.items():
            subcollection = bpy.data.collections.new(parent_name)
            subcollection.color_tag = 'COLOR_0' + str(idx_p % 8 + 1)
            collection.children.link(subcollection)
            for i, sub_name in enumerate(sub_names):
                subsubcollection = bpy.data.collections.new(sub_name)
                subsubcollection.color_tag = 'COLOR_0' + str(i % 8 + 1)
                subcollection.children.link(subsubcollection)
                if first_item:
                    first_item = False
                    self.populate_props(subsubcollection)   
            idx_p += 1
            
    def populate_props(self, collection):
        '''
        Populates two prop cubes to show file organization
        '''
        bpy.ops.mesh.primitive_cube_add()
        prop_cube = bpy.context.active_object
        prop_cube.name = "prop_0_temporary cube here"
        prop_cube.hide_render = True
        collection.objects.link(prop_cube)
        if bpy.context.scene.collection.objects.get(prop_cube.name):
            bpy.context.scene.collection.objects.unlink(prop_cube)

        bpy.ops.mesh.primitive_cube_add()
        extra_cube = bpy.context.active_object
        extra_cube.name = "extra_0_a matching extra for the cube"
        extra_cube.hide_render = True
        collection.objects.link(extra_cube)
        if bpy.context.scene.collection.objects.get(extra_cube.name):
            bpy.context.scene.collection.objects.unlink(extra_cube)

        # add text objects with descriptions
        bpy.ops.object.text_add()
        prop_text = bpy.context.active_object
        prop_text.name = "prop_text"
        prop_text.hide_render = True
        prop_text.data.body =   "Please place the objects of the appropriate types\n" + \
                                "in the corresponding collection with names starting with\n" + \
                                "'prop_{type_index}_whatever else' or 'extra_{type_index}_whatever else'.\n" + \
                                "\nThese two types are used to populate the building. The prop objects\n" + \
                                "are used to create the general shape of the building, while the extra\n" + \
                                "objects are used to decorate the building. Both types are randomly generated\n" + \
                                "from the collections. The {type_index} is used to match the props to their possible\n" + \
                                "extra pairs.\n\nWhile the props are selected individually (only one can be selected\n" + \
                                "for single position placement), the extras are selected as a group (all extras\n" + \
                                "can be selected for multiple position placement)."
        prop_text.data.size = 0.4
        prop_text.location = (2, -2, 0)
        collection.objects.link(prop_text)
        if bpy.context.scene.collection.objects.get(prop_text.name):
            bpy.context.scene.collection.objects.unlink(prop_text)


    def execute(self, context):
        if "MB_Design_System" not in bpy.data.collections:
            self.create_design_collection_template()
            self.report({'INFO'}, "Building template created")
        else:
            self.report({'WARNING'}, "The collection 'MB_Design_System' already exists. A new template was not created.")
        return {'FINISHED'}


class MB_HiddenObject(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    selected: bpy.props.BoolProperty(default=False)

def update_use_select_with_children(self, context):
    if not self.use_select_with_children:
        self.select_invisible_objects = False

class SelectWithChildrenPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    
    use_select_with_children: bpy.props.BoolProperty(
        name="Select with Children",
        description="When enabled, selecting an object will also select its children",
        default=False,
        update=update_use_select_with_children,
    )

    select_invisible_objects: bpy.props.BoolProperty(
        name="Select Invisible Objects",
        description="When enabled, selecting an object will also select its invisible children",
        default=False,
    )

    hidden_objects: bpy.props.CollectionProperty(type=MB_HiddenObject)


class MB_OT_RehideObjects(bpy.types.Operator):
    '''an operator to re-hide selected objects'''
    bl_idname = "mb.rehide_objects"
    bl_label = "Bulk Invisible"

    def execute(self, context):
        addon_prefs = context.preferences.addons[__name__].preferences

        to_remove = []
        for hidden_obj_data in addon_prefs.hidden_objects:
            if hidden_obj_data.selected:
                obj = bpy.data.objects.get(hidden_obj_data.name)
                if obj:
                    obj.hide_set(True)
                    to_remove.append(hidden_obj_data.name)

        for name in to_remove:
            addon_prefs.hidden_objects.remove(addon_prefs.hidden_objects.find(name))
                    
        return {'FINISHED'}


def select_objects(obj, addon_prefs, reveal_hidden=False):
    hidden_objs = []

    for o in obj.children_recursive:
        if reveal_hidden and o.hide_get():
            hidden_objs.append(o.name_full)
            o.hide_set(False)
        o.select_set(True)

    for o in hidden_objs:
        addon_prefs.hidden_objects.add().name = o
        addon_prefs.hidden_objects[-1].selected = False


def object_select_callback(*args):
    """
    Callback function for object selection.
    """
    obj = bpy.context.active_object
    addon_prefs = bpy.context.preferences.addons[__name__].preferences

    if addon_prefs.use_select_with_children and obj and obj.select_get():
        select_objects(obj, addon_prefs, addon_prefs.select_invisible_objects)


def subscribe_to_object_select():
    """
    Subscribe to object selection updates using Blender's message bus.
    """
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.LayerObjects, "active"),
        owner=object(),
        args=(),
        notify=object_select_callback,
        options={"PERSISTENT"},
    )


class MB_PT_MagicBuilderPanel(bpy.types.Panel):
    '''
    Panel for the Magic Builder addon.
    '''
    bl_idname = "OBJECT_PT_mb"
    bl_label = "Magic Builder"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MB"

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        col.label(text="Max Dimensions:")
        col.prop(context.scene, "mb_max_x")
        col.prop(context.scene, "mb_max_y")
        col.prop(context.scene, "mb_max_z")

        col = layout.column(align=True)
        col.label(text="Starting Rotation:")
        col.prop(context.scene, "mb_start_degree", text="Z-Rotation", slider=True)

        col = layout.column(align=True)
        col.label(text="Starting Location:", icon='WORLD')
        col.prop(context.scene, "mb_start_loc", text="X", index=0, slider=True)
        col.prop(context.scene, "mb_start_loc", text="Y", index=1, slider=True)
        col.prop(context.scene, "mb_start_loc", text="Z", index=2, slider=True)

        col = layout.column(align=True)
        col.label(text="Probability of adding each extra:")
        col.prop(context.scene, "mb_extra_probability", text="Prob", slider=True)

        col = layout.column(align=True)
        col.label(text="Add Roof:")
        col.prop(context.scene, "mb_add_roof")

        col = layout.column(align=True)
        col.label(text="Collection Name:")
        col.prop(context.scene, "mb_collection_name", text="", icon='OUTLINER_OB_FONT')

        col = layout.column(align=True)
        col.label(text="Design Collection Name:")
        col.prop_search(context.scene, "mb_design_collection_name", bpy.data, "collections", text="")

        row = layout.row()
        row.operator("mb.generate_building", icon='PLAY')

        row = layout.row()
        row.operator("mb.building_template_creator", icon='COLLECTION_NEW')

        addon_prefs = context.preferences.addons[__name__].preferences
        layout.prop(addon_prefs, "use_select_with_children", text="Select with Children", icon='LINKED')
        row = layout.row()
        row.enabled = addon_prefs.use_select_with_children
        row.prop(addon_prefs, "select_invisible_objects", text="Select Invisible Objects")

        layout.label(text="Re-hide objects:")

        if len(addon_prefs.hidden_objects) == 0:
            layout.label(text="No objects to re-hide", icon='INFO')
        else:
            box = layout.box()
            col = box.column()
            for hidden_obj_data in addon_prefs.hidden_objects:
                col.prop(hidden_obj_data, "selected", text=hidden_obj_data.name)

            bulk_invisible_op = layout.operator("mb.rehide_objects", icon='RESTRICT_VIEW_ON')
            

def register():
    # Registering the classes
    bpy.utils.register_class(MB_HiddenObject)
    bpy.utils.register_class(MB_PT_MagicBuilderPanel)
    bpy.utils.register_class(MB_OT_MagicBuilder)
    bpy.utils.register_class(MB_OT_BuildingTemplateCreator)
    bpy.utils.register_class(SelectWithChildrenPreferences)
    bpy.utils.register_class(MB_OT_RehideObjects)
    subscribe_to_object_select()
    

    bpy.types.WindowManager.mb_old_collection_deleted = bpy.props.BoolProperty(
        name="Old Collection Deleted",
        description="Indicates if the old collection has been deleted",
        default=False
    )

    bpy.types.Scene.mb_max_x = bpy.props.IntProperty(
        name="Max X",
        description="Maximum X dimension of the building. In blocks",
        default=2,
        min=1,
    )
    bpy.types.Scene.mb_max_y = bpy.props.IntProperty(
        name="Max Y",
        description="Maximum Y dimension of the building. In blocks",
        default=2,
        min=1
    )
    bpy.types.Scene.mb_max_z = bpy.props.IntProperty(
        name="Max Z",
        description="Maximum Z dimension of the building. In blocks",
        default=1,
        min=1
    )
    bpy.types.Scene.mb_start_degree = bpy.props.IntProperty(
        name="Start Degree",
        description="Starting Degree of Z-Axis rotation. In degrees (0-360)",
        default=0,
        min=0,
        max=360,
        subtype='ANGLE'
    )
    bpy.types.Scene.mb_start_loc = bpy.props.FloatVectorProperty(
        name="Starting Location",
        description="Starting Location of the first block",
        default=(0, 0, 0),
        subtype='XYZ'
    )
    bpy.types.Scene.mb_add_roof = bpy.props.BoolProperty(
        name="Add Roof",
        description="Whether to add a roof to the building",
        default=True
    )
    bpy.types.Scene.mb_collection_name = bpy.props.StringProperty(
        name="Collection Name",
        description="Name of the new collection where the building will be stored",
        default="New Building"
    )
    bpy.types.Scene.mb_design_collection_name = bpy.props.StringProperty(
        name="Design Collection Name",
        description="Name of the collection where the design of the building is stored. If you do not have a design collection, use the Create Building Template button to create one.",
        default="MB_Design_System"
    )
    bpy.types.Scene.mb_extra_probability = bpy.props.FloatProperty(
        name="Extra Probability",
        description="Probability of adding an extra block to the building",
        default=0.5,
        min=0,
        max=1
    )

def unregister():
    # Unregistering the classes
    bpy.utils.unregister_class(MB_HiddenObject)
    bpy.utils.unregister_class(MB_PT_MagicBuilderPanel)
    bpy.utils.unregister_class(MB_OT_MagicBuilder)
    bpy.utils.unregister_class(MB_OT_BuildingTemplateCreator)
    bpy.utils.unregister_class(SelectWithChildrenPreferences)
    bpy.utils.unregister_class(MB_OT_RehideObjects)
    
    del bpy.types.WindowManager.mb_old_collection_deleted
    del bpy.types.Scene.mb_max_x
    del bpy.types.Scene.mb_max_y
    del bpy.types.Scene.mb_max_z
    del bpy.types.Scene.mb_start_degree
    del bpy.types.Scene.mb_start_loc
    del bpy.types.Scene.mb_add_roof
    del bpy.types.Scene.mb_collection_name
    del bpy.types.Scene.mb_design_collection_name
