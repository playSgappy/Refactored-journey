import pygame
import sys
import random
import noise
import json

# 常量定义
TILE_SIZE = 32
MAP_WIDTH = 100   # 地图宽度（图块数量）
MAP_HEIGHT = 100  # 地图高度（图块数量）
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 900
INVENTORY_ROWS = 4   #物品栏行数
INVENTORY_COLS = 9   #物品栏列数

TILE_TYPES = {
    "grass": {"color": (100, 200, 100), "collision": False},
    "water": {"color": (50, 150, 250), "collision": True},
    "rock": {"color": (100, 100, 100), "collision": True},
    "path": {"color": (200, 180, 50), "collision": False},
}


# 颜色定义
COLORS = {
    "background": (40, 40, 40),
    "slot": (80, 80, 80),
    "selected": (200, 200, 0),
    "text": (255, 255, 255)
}

# 物品数据库
def load_item_database(filename="items.json"):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Item database not found.")
        return {}
ITEM_DATABASE = load_item_database()

# 物品类
class Item(pygame.sprite.Sprite):
    def __init__(self, item_id, quantity=1):
        super().__init__()
        self.item_id = item_id
        self.data = ITEM_DATABASE[item_id]
        self.image = pygame.image.load(self.data["image"]).convert_alpha()
        self.image = pygame.transform.scale(self.image, (TILE_SIZE, TILE_SIZE))
        self.rect = self.image.get_rect()
        self.quantity = quantity if self.data["stackable"] else 1

    def draw(self, surface, pos):
        surface.blit(self.image, pos)
        if self.data["stackable"]:
            font = pygame.font.Font(None, 24)
            text = font.render(str(self.quantity), True, COLORS["text"])
            surface.blit(text, (pos[0]+20, pos[1]+20))

# 背包类
class Inventory:
    def __init__(self):
        self.slots = [[None for _ in range(INVENTORY_COLS)] for _ in range(INVENTORY_ROWS)]
        self.selected_slot = (0, 0)
    
    def add_item(self, item):
        # 尝试堆叠已有物品
        if item.data["stackable"]:
            for y, row in enumerate(self.slots):
                for x, slot_item in enumerate(row):
                    if slot_item and slot_item.item_id == item.item_id:
                        slot_item.quantity += item.quantity
                        return True
        
        # 寻找空位
        for y in range(INVENTORY_ROWS):
            for x in range(INVENTORY_COLS):
                if not self.slots[y][x]:
                    self.slots[y][x] = item
                    return True
        return False
    
    def remove_item(self, pos, quantity=1):
        item = self.slots[pos[1]][pos[0]]
        if not item:
            return False
        
        if item.data["stackable"]:
            item.quantity -= quantity
            if item.quantity <= 0:
                self.slots[pos[1]][pos[0]] = None
        else:
            self.slots[pos[1]][pos[0]] = None
        return True
    
    def save_to_file(self, filename="save.json"):
        save_data = []
        for y, row in enumerate(self.slots):
            for x, item in enumerate(row):
                if item:
                    save_data.append({
                        "x": x,
                        "y": y,
                        "item_id": item.item_id,
                        "quantity": item.quantity
                    })
        with open(filename, "w") as f:
            json.dump(save_data, f)
    
    def load_from_file(self, filename="save.json"):
        try:
            with open(filename, "r") as f:
                save_data = json.load(f)
                for entry in save_data:
                    item = Item(entry["item_id"], entry["quantity"])
                    self.slots[entry["y"]][entry["x"]] = item
        except FileNotFoundError:
            print("No save file found, starting fresh inventory")

# 物品栏界面
class InventoryUI:
    def __init__(self, inventory):
        self.inventory = inventory
        self.visible = False  # 默认隐藏
        self.slot_size = 48  # 槽位大小
        self.padding = 5     # 槽位间距
        self.ui_width = INVENTORY_COLS * (self.slot_size + self.padding) + self.padding
        self.ui_height = INVENTORY_ROWS * (self.slot_size + self.padding) + self.padding
        self.position = ((WINDOW_WIDTH - self.ui_width) // 2, WINDOW_HEIGHT - self.ui_height - 20)  # 正下方居中

    def toggle_visibility(self):
        self.visible = not self.visible

    def draw(self, surface):
        if not self.visible:
            return
        
        # 绘制半透明背景
        bg_surface = pygame.Surface((self.ui_width, self.ui_height), pygame.SRCALPHA)
        bg_surface.fill((40, 40, 40, 200))  # 半透明背景
        surface.blit(bg_surface, self.position)

        # 绘制物品槽
        for y in range(INVENTORY_ROWS):
            for x in range(INVENTORY_COLS):
                slot_pos = (
                    self.position[0] + self.padding + x * (self.slot_size + self.padding),
                    self.position[1] + self.padding + y * (self.slot_size + self.padding)
                )
                
                # 绘制槽位边框
                border_color = COLORS["selected"] if (x, y) == self.inventory.selected_slot else COLORS["slot"]
                pygame.draw.rect(surface, border_color, (slot_pos[0]-1, slot_pos[1]-1, self.slot_size+2, self.slot_size+2), 2)
                
                # 绘制物品
                item = self.inventory.slots[y][x]
                if item:
                    item_image = pygame.transform.scale(item.image, (self.slot_size-4, self.slot_size-4))
                    surface.blit(item_image, (slot_pos[0]+2, slot_pos[1]+2))
                    
                    # 绘制数量文字
                    if item.data["stackable"]:
                        font = pygame.font.Font(None, 20)
                        text = font.render(str(item.quantity), True, COLORS["text"])
                        surface.blit(text, (slot_pos[0]+30, slot_pos[1]+30))

    def handle_click(self, mouse_pos):
        if not self.visible:
            return False
        
        # 转换为相对坐标
        rel_x = mouse_pos[0] - self.position[0] - self.padding
        rel_y = mouse_pos[1] - self.position[1] - self.padding
        
        # 计算点击的格子
        x = rel_x // (self.slot_size + self.padding)
        y = rel_y // (self.slot_size + self.padding)
        
        if 0 <= x < INVENTORY_COLS and 0 <= y < INVENTORY_ROWS:
            self.inventory.selected_slot = (x, y)
            return True
        return False
# 玩家类
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # 加载玩家头像
        self.image = pygame.image.load("textures/steve.png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (32, 32))  # 调整大小为32x32
        self.rect = self.image.get_rect()
        self.rect.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        self.speed = 5
        self.inventory = Inventory()
        self.ui = InventoryUI(self.inventory)
        self.b_pressed = False  # 用于检测B键是否按下

    def update(self, keys, items):
        # 检测B键按下
        if keys[pygame.K_b]:
            if not self.b_pressed:  # 防止持续触发
                self.ui.toggle_visibility()
                self.b_pressed = True
        else:
            self.b_pressed = False

        # 玩家移动
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.rect.y -= self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.rect.y += self.speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.rect.x += self.speed

        map_width_px = MAP_WIDTH * TILE_SIZE
        map_height_px = MAP_HEIGHT * TILE_SIZE

        # 限制角色在屏幕范围内
        if self.rect.x < 0:
            self.rect.x = 0
        if self.rect.x > map_width_px - 32:
            self.rect.x = map_width_px - 32
        if self.rect.y < 0:
            self.rect.y = 0
        if self.rect.y > map_height_px - 32:
            self.rect.y = map_height_px - 32
        # 拾取物品
        for item in items:
            if self.rect.colliderect(item.rect):
                if self.inventory.add_item(item):
                    item.kill()  # 从地图上移除物品

        # 物品使用
        if keys[pygame.K_e]:
            self.use_selected_item()

    def use_selected_item(self):
        x, y = self.inventory.selected_slot
        item = self.inventory.slots[y][x]
        if item:
            print(f"Using {item.data['name']}")
            self.inventory.remove_item((x, y))

# 图块类
class Tile(pygame.sprite.Sprite):
    def __init__(self, color, x, y, collision):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.collision = collision

# 地图类
class Map:
    def __init__(self, map_data):
        self.map_data = map_data
        self.tile_group = pygame.sprite.Group()
        self.visible_tiles = pygame.sprite.Group()

    def load_chunk(self, player_rect, chunk_size=50):
        # 清除之前加载的所有可见图块
        self.visible_tiles.empty()
        
        # 获取玩家当前位置
        player_x, player_y = player_rect.centerx // TILE_SIZE, player_rect.centery // TILE_SIZE
        
        # 计算要加载的区域
        start_x = max(player_x - chunk_size // 2, 0)
        start_y = max(player_y - chunk_size // 2, 0)
        end_x = min(player_x + chunk_size // 2, MAP_WIDTH)
        end_y = min(player_y + chunk_size // 2, MAP_HEIGHT)

        # 加载新的图块
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile_type = self.map_data[y][x]
                tile_config = TILE_TYPES.get(tile_type, TILE_TYPES["grass"])
                tile = Tile(
                    tile_config["color"],
                    x * TILE_SIZE,
                    y * TILE_SIZE,
                    tile_config["collision"]
                )
                self.visible_tiles.add(tile)

    def draw(self, surface, camera):
        for tile in self.visible_tiles:
            if camera.is_visible(tile.rect):
                surface.blit(tile.image, camera.apply(tile.rect))

# 摄像机类
class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height
    
    def apply(self, rect):
        return rect.move(-self.camera.x, -self.camera.y)
    
    def update(self, target):
        x = target.x - self.width // 2
        y = target.y - self.height // 2
        
        # 限制摄像机范围
        map_width_px = MAP_WIDTH * TILE_SIZE
        map_height_px = MAP_HEIGHT * TILE_SIZE
        x = max(0, min(x, map_width_px - self.width))
        y = max(0, min(y, map_height_px - self.height))
        
        self.camera = pygame.Rect(x, y, self.width, self.height)
    
    def is_visible(self, rect):
        return self.camera.colliderect(rect)

# 地图生成函数
def generate_perlin_map(seed=None):
    if seed is not None:
        random.seed(seed)  # 设置随机种子
    map_data = []
    scale = 0.1
    offset_x = random.randint(0, 10000)
    offset_y = random.randint(0, 10000)
    
    for y in range(MAP_HEIGHT):
        row = []
        for x in range(MAP_WIDTH):
            value = noise.pnoise2(
                (x + offset_x) * scale,
                (y + offset_y) * scale,
                octaves=1,
                persistence=0.5,
                lacunarity=2.0
            )
            if value < -0.5:
                tile_type = "water"
            elif value < 0:
                tile_type = "grass"
            else:
                tile_type = "rock"
            row.append(tile_type)
        map_data.append(row)
    return map_data

# 在地图上随机生成物品
def generate_items(map_data, existing_items):
    items = pygame.sprite.Group()
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            for item_type, item_data in ITEM_DATABASE.items():
                if map_data[y][x] == "grass" and random.random() < item_data["spawn_probability"]:
                    # 检查当前位置是否有其他物品
                    overlap = False
                    for existing_item in existing_items:
                        if existing_item.rect.colliderect(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)):
                            overlap = True
                            break
                    
                    if not overlap:
                        item = Item(item_type)
                        item.rect.topleft = (x * TILE_SIZE, y * TILE_SIZE)
                        items.add(item)
                        existing_items.add(item)  # 将物品添加到已有物品集合中
    return items

# 主函数
def main():
    pygame.init()
    window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Farm Life")
    clock = pygame.time.Clock()

    # 生成地图
    map_data = generate_perlin_map()
    game_map = Map(map_data)

    # 创建一个空集合用于存储已经生成的物品
    existing_items = pygame.sprite.Group()

    # 生成物品
    items = generate_items(map_data, existing_items)

    # 初始化游戏元素
    player = Player()
    camera = Camera(WINDOW_WIDTH, WINDOW_HEIGHT)
    player.inventory.load_from_file()

    # 初始化加载地图
    game_map.load_chunk(player.rect)

    running = True
    while running:
        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                player.inventory.save_to_file()
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键点击
                    player.ui.handle_click(event.pos)

        # 玩家移动
        keys = pygame.key.get_pressed()
        player.update(keys, items)

        # 更新摄像机
        camera.update(player.rect)

        #加载地图
        game_map.load_chunk(player.rect)

        # 绘制
        window.fill((0, 0, 0))
        game_map.draw(window, camera)
        for item in items:
            if camera.is_visible(item.rect):
                item_screen_pos = camera.apply(item.rect).topleft
                item.draw(window, item_screen_pos)
        window.blit(player.image, camera.apply(player.rect))

        # 绘制背包界面（如果可见）
        player.ui.draw(window)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()