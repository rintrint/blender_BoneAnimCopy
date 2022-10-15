# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name" : "Bone Animation Copy Tool",
    "author" : "Kumopult <kumopult@qq.com>",
    "description" : "Copy animation between different armature by bone constrain",
    "blender" : (3, 3, 0),
    "version" : (0, 0, 4),
    "location" : "View 3D > Toolshelf",
    "warning" : "因为作者很懒所以没写英文教学！",
    "category" : "Animation",
    "doc_url": "https://github.com/kumopult/blender_BoneAnimCopy",
    "tracker_url": "https://space.bilibili.com/1628026",
    # VScode调试：Ctrl + Shift + P
}

import bpy
from . import data
from . import mapping
from .utilfuncs import *

class BAC_PT_Panel(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BoneAnimCopy"
    bl_label = "Bone Animation Copy Tool"
    
    def draw(self, context):
        layout = self.layout
        
        if context.object != None and context.object.type == 'ARMATURE':
            s = get_state()
            
            split = layout.row().split(factor=0.2)
            left = split.column()
            right = split.column()
            left.label(text='映射骨架:')
            left.label(text='约束目标:')
            right.label(text=context.object.name, icon='ARMATURE_DATA', translate=False)
            right.prop(s, 'selected_target', text='', icon='ARMATURE_DATA', translate=False)
            
            if s.target == None:
                layout.label(text='选择另一骨架对象作为约束目标以继续操作', icon='INFO')
            else:
                mapping.draw_panel(layout.row())
                row = layout.row()
                row.prop(s, 'preview', text='预览约束', icon= 'HIDE_OFF' if s.preview else 'HIDE_ON')
                row.operator('kumopult_bac.bake', text='烘培动画', icon='NLA')
        else:
            layout.label(text='未选中骨架对象', icon='ERROR')


class BAC_State(bpy.types.PropertyGroup):
    selected_target: bpy.props.PointerProperty(
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE' and obj != bpy.context.object,
        update=lambda self, ctx: get_state().update_target()
    )
    target: bpy.props.PointerProperty(type=bpy.types.Object)
    owner: bpy.props.PointerProperty(type=bpy.types.Object)
    
    mappings: bpy.props.CollectionProperty(type=data.BAC_BoneMapping)
    active_mapping: bpy.props.IntProperty(default=-1)
    selected_count:bpy.props.IntProperty(default=0)
    
    editing_type: bpy.props.IntProperty(description="用于记录面板类型")
    preview: bpy.props.BoolProperty(
        default=True, 
        description="开关所有约束以便预览烘培出的动画之类的",
        update=lambda self, ctx: get_state().update_preview()
    )
    calc_offset: bpy.props.BoolProperty(default=True, description="设定映射目标时自动计算旋转偏移")
    ortho_offset: bpy.props.BoolProperty(default=True, description="将计算结果近似至90°的倍数")
    
    def update_target(self):
        self.owner = bpy.context.object
        self.target = self.selected_target

        for m in self.mappings:
            m.apply()
    
    def update_preview(self):
        for m in self.mappings:
            m.set_enable(self.preview)
    
    def get_target_armature(self):
        return self.target.data

    def get_owner_armature(self):
        return self.owner.data
    
    def get_target_pose(self):
        return self.target.pose

    def get_owner_pose(self):
        return self.owner.pose

    def get_active_mapping(self):
        return self.mappings[self.active_mapping]
    
    def get_mapping_by_target(self, name):
        if name != "":
            for i, m in enumerate(self.mappings):
                if m.target == name:
                    return m, i
        return None, -1

    def get_mapping_by_owner(self, name):
        if name != "":
            for i, m in enumerate(self.mappings):
                if m.owner == name:
                    return m, i
        return None, -1

    def get_selection(self):
        indices = []

        if self.selected_count == 0 and len(self.mappings) > self.active_mapping >= 0:
            indices.append(self.active_mapping)
        else:
            for i in range(len(self.mappings) - 1, -1, -1):
                if self.mappings[i].selected:
                    indices.append(i)
        return indices
    
    def add_mapping(self, owner, target, index=-1):
        # 未传入index时，以激活项作为index
        if index == -1:
            self.active_mapping += 1
            index = self.active_mapping
        # 这里需要检测一下目标骨骼是否已存在映射
        m, i = self.get_mapping_by_owner(owner)
        if m:
            # 若已存在，则覆盖原本的源骨骼，并返回映射和索引值
            m.target = target
            return m, i
        else:
            # 若不存在，则新建映射，同样返回映射和索引值
            m = self.mappings.add()
            m.selected_owner = owner
            m.target = target
            # return m, len(self.mappings) - 1
            self.mappings.move(len(self.mappings) - 1, index)
            return self.mappings[index], index
    
    def remove_mapping(self):
        for i in self.get_selection():
            self.mappings[i].clear()
            self.mappings.remove(i)
        if self.selected_count == 0:
            self.active_mapping = min(self.active_mapping, len(self.mappings) - 1)
        # 选中状态更新
        self.selected_count = 0

classes = (
	BAC_PT_Panel, 
	*data.classes,
	*mapping.classes,
	BAC_State,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.kumopult_bac = bpy.props.PointerProperty(type=BAC_State)
    print("hello kumopult!")

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Object.kumopult_bac
    print("goodbye kumopult!")
