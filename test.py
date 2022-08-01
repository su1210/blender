import bpy         #blender作為python的模塊
import os.path     #獲取文件的屬性
import math
import sys
#sys模組內含很多函式方法和變數，用來處理Python執行時配置以及資源，從而可以與當前程式之外的系統環境互動

C = bpy.context
D = bpy.data
scene = D.scenes['Scene']

# cameras: a list of camera positions
# a camera position is defined by two parameters: (theta, phi),
#相機位置由兩個參數定義：(theta, phi)

# where we fix the "r" of (r, theta, phi) in spherical coordinate system.

# 5 orientations: front, right, back, left, top
# cameras = [(60, 0), (60, 90), (60, 180), (60, 270),(0, 0)]

# multiview  with inter-deg elevation   具有度間仰角的多視圖
fixed_view = 60
inter = 30
cameras = [(fixed_view, i) for i in range(0, 360, inter)] # output 12(360/30=12) multiview images

render_setting = scene.render

# output image size = (W, H)  輸出圖片大小
w = 224
h = 224
render_setting.resolution_x = w*2   #渲染圖像中的水平像素數
render_setting.resolution_y = h*2   #渲染圖像中的垂直像素數


'''****************************************************************'''
#當讀不到路徑檔案時,輸出(1)

def main():
    argv = sys.argv
    argv = argv[argv.index('--') + 1:]

    if len(argv) != 2:
        print('phong.py args: <3d mesh path> <image dir>')  #(1)
        exit(-1)

    model_path = argv[0]    # input: path of single .off or dataset.txt
    image_dir = argv[1]     	# input: path to save multiview images

    # blender has no native support for off files   blender沒有對.off文件的支援
    #install_off_addon()
    init_camera()
    fix_camera_to_origin()

    '''*************************************************'''
#mesh path 網格路徑
#image dir 圖像目錄
#確認輸入的檔案

    if model_path.split('.')[-1] == 'off':     #以點當作分隔符號，查看倒數第一個元素是否為off
        print('model path is ********', model_path) 
        do_model(model_path, image_dir)
    elif model_path.split('.')[-1] == 'txt':
        with open(model_path) as f:
            models = f.read().splitlines()
        for model in models:
            print('model path is ********', model) 
            do_model(model, image_dir)
    else:
        print('......Please input correct parameters......')
        exit(-1)
'''****************************************************************'''
#確認是否可以安裝OFF addon  ？？有沒有都可？？

def install_off_addon():
    try:
        bpy.ops.wm.addon_install(
            overwrite=False,
            filepath=os.path.dirname(__file__) +
            '/blender-off-addon/import_off.py'
        )
        bpy.ops.wm.addon_enable(module='import_off')
    except Exception:
        print("""Import blender-off-addon failed.
              Did you pull the blender-off-addon submodule?
              $ git submodule update --recursive --remote
              """)
        exit(-1)

#相機設置

def init_camera():
    cam = D.objects['Camera']     #可視化目標
    # select the camera object
    scene.objects.active = cam
    cam.select = True

    # set the rendering mode to orthogonal and scale   將渲染模式設置為正交和縮放
    C.object.data.type = 'ORTHO'
    C.object.data.ortho_scale = 2.


def fix_camera_to_origin():
    origin_name = 'Origin'

    # create origin
    try:
        origin = D.objects[origin_name]
    except KeyError:
        bpy.ops.object.empty_add(type='SPHERE')
        D.objects['Empty'].name = origin_name
        origin = D.objects[origin_name]

    origin.location = (0, 0, 0)

    cam = D.objects['Camera']
    scene.objects.active = cam
    cam.select = True

    if 'Track To' not in cam.constraints:
        bpy.ops.object.constraint_add(type='TRACK_TO')

    cam.constraints['Track To'].target = origin
    cam.constraints['Track To'].track_axis = 'TRACK_NEGATIVE_Z'
    cam.constraints['Track To'].up_axis = 'UP_Y'


def do_model(model_path, image_dir):
    #model_path= 'F:\\home\\su\\blender\\teatop\\teatop_1.off'
    #image_dir = 'F:\\home\\su\\blender\\train'
    name = load_model(model_path) 
    center_model(name)
    normalize_model(name)

    image_subdir = os.path.join(image_dir, name.split('_')[0], name) 
    for i, c in enumerate(cameras):
        move_camera(c)
        render()
        save(image_subdir, '%s_%d' % (name, i))

    delete_model(name)


def load_model(model_path):
    d = os.path.dirname(model_path) # invalide for .off file
    ext = model_path.split('.')[-1] # ext: 'off'

    # Attention!  win10: ..path.split('\\')  linux: ..path.split('/')
    _model_path_tmp = model_path.split('/')[-1] 
    name = os.path.basename(_model_path_tmp).split('.')[0] 
    # handle weird object naming by Blender for stl files
    if ext == 'stl':
        name = name.title().replace('_', ' ')

    if name not in D.objects:
        print('loading :' + name)
        if ext == 'stl':
            bpy.ops.import_mesh.stl(filepath=model_path, directory=d,
                                    filter_glob='*.stl')
        elif ext == 'off':
            bpy.ops.import_mesh.off(filepath=model_path, filter_glob='*.off')
        elif ext == 'obj':
            bpy.ops.import_scene.obj(filepath=model_path, filter_glob='*.obj')
        else:
            print('Currently .{} file type is not supported.'.format(ext))
            exit(-1)
    return name 


def delete_model(name):
    for ob in scene.objects:
        if ob.type == 'MESH' and ob.name.startswith(name):
            ob.select = True
        else:
            ob.select = False
    bpy.ops.object.delete()


def center_model(name):
    bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN')
    D.objects[name].location = (0, 0, 0)


def normalize_model(name):
    obj = D.objects[name]
    dim = obj.dimensions
    print('original dim:' + str(dim))
    if max(dim) > 0:
        dim = dim / max(dim)
    obj.dimensions = dim

    print('new dim:' + str(dim))


def move_camera(coord):
    def deg2rad(deg):
        return deg * math.pi / 180.

    r = 3.
    theta, phi = deg2rad(coord[0]), deg2rad(coord[1])
    loc_x = r * math.sin(theta) * math.cos(phi)
    loc_y = r * math.sin(theta) * math.sin(phi)
    loc_z = r * math.cos(theta)

    D.objects['Camera'].location = (loc_x, loc_y, loc_z)


def render():
    bpy.ops.render.render()


def save(image_dir, name):
    path = os.path.join(image_dir, name + '.png')
    D.images['Render Result'].save_render(filepath=path)
    print('save to ' + path)


if __name__ == '__main__':
    main()
