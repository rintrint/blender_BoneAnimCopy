import bpy
from .utilfuncs import *
from math import pi
from mathutils import Matrix, Euler

class BAC_BoneMapping(bpy.types.PropertyGroup):
    def update_owner(self, context):
        # 更改自身骨骼，需要先清空旧的约束再生成新的约束
        self.clear()
        self.owner = self.selected_owner
        self.apply()

    def update_target(self, context):
        # 更改目标骨骼，需要刷新约束上的目标
        s = get_state()
        if self.is_valid() and s.calc_offset:
            # 计算旋转偏移
            euler_offset = ((s.target.matrix_world @ self.get_target().matrix).inverted() @ (s.owner.matrix_world @ self.get_owner().matrix)).to_euler()
            if s.ortho_offset:
                step = pi * 0.5
                euler_offset[0] = round(euler_offset[0] / step) * step
                euler_offset[1] = round(euler_offset[1] / step) * step
                euler_offset[2] = round(euler_offset[2] / step) * step
            if euler_offset != None or Euler.zero():
                self.offset[0] = euler_offset[0]
                self.offset[1] = euler_offset[1]
                self.offset[2] = euler_offset[2]
                self.has_rotoffs = True
        self.apply()
    
    def update_rotoffs(self, context):
        if self.has_rotoffs:
            # 开启旋转偏移，需要新建约束
            self.update_offset(context)
        else:
            # 关闭旋转偏移，需要清除约束
            self.remove(self.get_rr())
        
    def update_loccopy(self, context):
        if self.has_loccopy:
            self.get_cp()
        else:
            self.remove(self.get_cp())
    
    def update_ik(self, context):
        if self.has_ik:
            self.get_ik()
        else:
            self.remove(self.get_ik())

    def update_offset(self, context):
        rr = self.get_rr()
        rr.to_min_x_rot = self.offset[0]
        rr.to_min_y_rot = self.offset[1]
        rr.to_min_z_rot = self.offset[2]

    selected_owner: bpy.props.StringProperty(
        name="自身骨骼", 
        description="将对方骨骼的旋转复制到自身的哪根骨骼上？", 
        update=update_owner
    )
    owner: bpy.props.StringProperty()
    target: bpy.props.StringProperty(
        name="约束目标", 
        description="从对方骨架中选择哪根骨骼作为约束目标？", 
        update=update_target
    )

    has_rotoffs: bpy.props.BoolProperty(
        name="旋转偏移", 
        description="附加额外约束，从而在原变换结果的基础上进行额外的旋转", 
        update=update_rotoffs
    )
    has_loccopy: bpy.props.BoolProperty(
        name="位置映射", 
        description="附加额外约束，从而使目标骨骼跟随原骨骼的世界坐标运动，通常应用于根骨骼、武器等", 
        update=update_loccopy
    )
    has_ik: bpy.props.BoolProperty(
        name="IK",
        description="附加额外约束，从而使目标骨骼跟随原骨骼进行IK矫正，通常应用于手掌、脚掌",
        update=update_ik
    )
    offset: bpy.props.FloatVectorProperty(
        name="旋转偏移量", 
        description="世界坐标下复制旋转方向后，在本地坐标下进行的额外旋转偏移。通常只需要调整Y旋转", 
        min=-pi,
        max=pi,
        subtype='EULER',
        update=update_offset
    )

    def update_selected(self, context):
        get_state().selected_count += 1 if self.selected else -1
    
    selected: bpy.props.BoolProperty(update=update_selected)

    def con_list(self):
        return {
            self.get_cr: True,
            self.get_rr: self.has_rotoffs,
            self.get_cp: self.has_loccopy,
            self.get_ik: self.has_ik
        }
    
    def get_owner(self):
        return get_state().get_owner_pose().bones.get(self.owner)

    def get_target(self):
        return get_state().get_target_pose().bones.get(self.target)

    def is_valid(self):
        return (self.get_owner() != None and self.get_target() != None)
    

    def apply(self):
        if not self.get_owner():
            return
        s = get_state()

        for get_con, has_con in self.con_list().items():
            if has_con:
                con = get_con()
                con.target = s.target
                con.subtarget = self.target
                if bpy.app.version >= (3, 0, 0):
                    con.enabled = self.is_valid()
                else:
                    con.mute = not self.is_valid()

        if self.has_rotoffs:
            rr = self.get_rr()
            rr.to_min_x_rot = self.offset[0]
            rr.to_min_y_rot = self.offset[1]
            rr.to_min_z_rot = self.offset[2]


    def clear(self):
        for get_con, has_con in self.con_list().items():
            if has_con:
                self.remove(get_con())
    
    def remove(self, constraint):
        if not self.get_owner():
            return
        # get_state().get_owner_pose().bones.get(self.owner).constraints.remove(constraint)
        self.get_owner().constraints.remove(constraint)
    
    def set_enable(self, state):
        if not self.is_valid():
            return
        for get_con, has_con in self.con_list().items():
            if has_con:
                if bpy.app.version >= (3, 0, 0):
                    get_con().enabled = state
                else:
                    get_con().mute = not state

    def get_cr(self):
        if self.get_owner():
            con = self.get_owner().constraints
        else:
            return None
        
        def new_cr():
            cr = con.new(type='COPY_ROTATION')
            cr.name = 'BAC_ROT_COPY'
            cr.show_expanded = False
            cr.target = get_state().target
            cr.subtarget = self.target
            if bpy.app.version >= (3, 0, 0):
                cr.enabled = self.is_valid()
            else:
                cr.mute = not self.is_valid()
            return cr
        
        return con.get('BAC_ROT_COPY') or new_cr()
        
    def get_rr(self):
        if self.get_owner():
            con = self.get_owner().constraints
        else:
            return None
        
        def new_rr():
            rr = con.new(type='TRANSFORM')
            rr.name = 'BAC_ROT_ROLL'
            rr.map_to = 'ROTATION'
            rr.owner_space = 'CUSTOM'
            rr.target = rr.space_object = get_state().target
            rr.subtarget = rr.space_subtarget = self.target
            rr.show_expanded = False
            if bpy.app.version >= (3, 0, 0):
                rr.enabled = self.is_valid()
            else:
                rr.mute = not self.is_valid()
            return rr
        
        return con.get('BAC_ROT_ROLL') or new_rr()
        
    def get_cp(self):
        if self.get_owner():
            con = self.get_owner().constraints
        else:
            return None

        def new_cp():
            cp = con.new(type='COPY_LOCATION')
            cp.name = 'BAC_LOC_COPY'
            cp.show_expanded = False
            cp.target = get_state().target
            cp.subtarget = self.target
            if bpy.app.version >= (3, 0, 0):
                cp.enabled = self.is_valid()
            else:
                cp.mute = not self.is_valid()
            return cp
        
        return con.get('BAC_LOC_COPY') or new_cp()

    def get_ik(self):
        if self.get_owner():
            con = self.get_owner().constraints
        else:
            return None
        
        def new_ik():
            ik = con.new(type='IK')
            ik.name = 'BAC_IK'
            ik.show_expanded = False
            ik.target = get_state().target
            ik.subtarget = self.target
            ik.chain_count = 2
            ik.use_tail = False
            if bpy.app.version >= (3, 0, 0):
                ik.enabled = self.is_valid()
            else:
                ik.mute = not self.is_valid()
            return ik
        
        return con.get('BAC_IK') or new_ik()

classes = (
	BAC_BoneMapping,
)