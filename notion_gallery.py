import customtkinter as ctk
import tkinter as tk
from tkinter import font as tkfont
from tkinter import filedialog, messagebox
from PIL import Image
import json
import os
import shutil
import uuid
import platform
import re

# ==========================================
# 1. 폰트 및 다크/라이트 테마 색상 설정
# ==========================================
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

BG_COLOR = ("#FFFFFF", "#191919")
CARD_BG = ("#F7F7F5", "#252525") 
TEXT_MAIN = ("#37352F", "#EAEAEA") 
TEXT_SUB = ("#787774", "#9E9E9E")  
HOVER_BG = ("#E5E7EB", "#333333")
CODE_BG = ("#F3F4F6", "#1E1E1E")
DEL_FG = ("#FFE5E5", "#4A2222")
DEL_TEXT = ("#D32F2F", "#FF8A8A")
DEL_HOVER = ("#FFCDD2", "#662A2A")

DATA_FILE = "gallery_data.json"
IMG_FOLDER = "gallery_images"

FONT_TITLE = None
FONT_SUBTITLE = None
FONT_NORMAL = None
FONT_TAG = None
FONT_PROMPT = ("Consolas", 13)

def setup_fonts():
    global FONT_TITLE, FONT_SUBTITLE, FONT_NORMAL, FONT_TAG
    available_fonts = tkfont.families()
    pref_fonts = ["Pretendard", "Noto Sans KR", "Apple SD Gothic Neo", "맑은 고딕", "Malgun Gothic", "sans-serif"]
    best_font = "sans-serif"
    for font in pref_fonts:
        if font in available_fonts:
            best_font = font; break
    FONT_TITLE = (best_font, 36, "bold")
    FONT_SUBTITLE = (best_font, 16, "bold")
    FONT_NORMAL = (best_font, 14)
    FONT_TAG = (best_font, 12)

def center_window(window, parent, width, height, mode="center"):
    px = parent.winfo_rootx(); py = parent.winfo_rooty()
    pw = parent.winfo_width(); ph = parent.winfo_height()
    if pw < 100: pw = 1200
    if ph < 100: ph = 850

    if mode == "center":
        x = px + (pw - width) // 2; y = py + (ph - height) // 2
    elif mode == "side":
        x = px + pw - width; y = py; height = ph
    elif mode == "full":
        x = px; y = py; width = pw; height = ph
    window.geometry(f"{width}x{height}+{x}+{y}")

# ==========================================
# 커스텀 팝업창
# ==========================================
class CustomDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, text, initial_name=""):
        super().__init__(parent)
        self.title(title)
        self.configure(fg_color=BG_COLOR)
        # 💡 강제 최상단 유지(-topmost)를 지우고 메인창에 종속되게 설정하여 파일창 가림 현상 방지
        self.transient(parent) 
        self.grab_set() # 모달 유지
        self.resizable(False, False)
        self.result_name = None
        center_window(self, parent, 400, 180)

        ctk.CTkLabel(self, text=text, font=FONT_SUBTITLE, text_color=TEXT_MAIN).pack(pady=(20, 10))
        self.name_entry = ctk.CTkEntry(self, font=FONT_NORMAL, height=35, fg_color=CARD_BG, text_color=TEXT_MAIN)
        self.name_entry.pack(fill="x", padx=40, pady=5)
        self.name_entry.insert(0, initial_name)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", pady=15)
        ctk.CTkButton(btn_frame, text="확인", width=100, font=FONT_NORMAL, command=self.on_ok).pack(side="right", padx=(5, 40))
        ctk.CTkButton(btn_frame, text="취소", width=100, font=FONT_NORMAL, fg_color=HOVER_BG, text_color=TEXT_MAIN, hover_color=CARD_BG, command=self.on_cancel).pack(side="right", padx=5)

        self.name_entry.bind("<Return>", lambda e: self.on_ok())
        self.name_entry.focus()
        self.wait_window()

    def on_ok(self):
        self.result_name = self.name_entry.get().strip()
        self.destroy()

    def on_cancel(self): self.destroy()

# ==========================================
# 메인 앱 클래스
# ==========================================
class NotionGalleryApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        setup_fonts() 
        self.title("내 프롬프트 갤러리")
        self.geometry("1300x900")
        self.configure(fg_color=BG_COLOR)

        if not os.path.exists(IMG_FOLDER): os.makedirs(IMG_FOLDER)

        self.data = self.load_data()
        self.current_frame = None
        self.field_widgets = [] 
        self.current_cards = [] 
        self.view_mode = "gallery" 
        self.temp_tags = [] 
        self.search_query = ""
        self.filter_tag = "전체"
        self.current_category = None
        
        self.show_home_page()

    def toggle_theme(self):
        current = ctk.get_appearance_mode()
        if current == "Light": ctk.set_appearance_mode("Dark")
        else: ctk.set_appearance_mode("Light")

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cat in data.get("categories", {}).values():
                        if "desc" not in cat: cat["desc"] = "설명을 입력하세요."
                        for item in cat.get("items", []):
                            if "id" not in item: item["id"] = str(uuid.uuid4())
                            if "fields" not in item:
                                item["fields"] = [{"title": "프롬프트", "content": item.pop("positive", item.pop("prompt", "")), "height": 150}]
                    return data
            except Exception: pass
        return {"title": "내 갤러리", "categories": {}}

    def save_data(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def load_image_safe(self, path, width, height):
        try:
            if path and os.path.exists(path):
                return ctk.CTkImage(light_image=Image.open(path), size=(width, height))
        except Exception: pass
        return ctk.CTkImage(light_image=Image.new('RGB', (width, height), color='#A0A0A0'), size=(width, height))

    def switch_frame(self, new_frame_func, *args):
        if self.current_frame: self.current_frame.destroy()
        self.current_frame = ctk.CTkFrame(self, fg_color=BG_COLOR)
        self.current_frame.pack(fill="both", expand=True)
        new_frame_func(self.current_frame, *args)

    # --- 1. 메인 홈 ---
    def show_home_page(self, container=None):
        self.current_category = None
        if container is None:
            container = ctk.CTkFrame(self, fg_color=BG_COLOR)
            container.pack(fill="both", expand=True)
            self.current_frame = container

        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=80, pady=(60, 20))
        
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(title_frame, text=self.data["title"], font=FONT_TITLE, text_color=TEXT_MAIN).pack(side="left")
        
        ctk.CTkButton(title_frame, text="이름 수정", width=60, fg_color=HOVER_BG, text_color=TEXT_SUB, hover_color=CARD_BG, font=FONT_NORMAL, command=self.edit_main_title).pack(side="left", padx=20)
        
        theme_text = "🌙 다크" if ctk.get_appearance_mode() == "Light" else "🌞 라이트"
        ctk.CTkButton(title_frame, text=theme_text, width=80, fg_color=CARD_BG, text_color=TEXT_MAIN, hover_color=HOVER_BG, font=FONT_NORMAL, command=lambda: [self.toggle_theme(), self.switch_frame(self.show_home_page)]).pack(side="right")

        list_frame = ctk.CTkFrame(container, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, padx=80, pady=10)

        for cat_name, cat_data in self.data["categories"].items():
            row_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=5)
            
            cat_btn = ctk.CTkButton(row_frame, text=f"📂 {cat_name}", font=FONT_SUBTITLE, fg_color="transparent", text_color=TEXT_MAIN, hover_color=CARD_BG, anchor="w", height=45, command=lambda n=cat_name: self.switch_frame(self.show_gallery_page, n))
            cat_btn.pack(side="left", fill="x", expand=True)
            
            btn_box = ctk.CTkFrame(row_frame, fg_color="transparent")
            btn_box.pack(side="right", padx=5)
            ctk.CTkButton(btn_box, text="수정", width=50, fg_color=HOVER_BG, text_color=TEXT_MAIN, hover_color=CARD_BG, font=FONT_NORMAL, command=lambda n=cat_name: self.edit_category(n)).pack(side="left", padx=5)
            ctk.CTkButton(btn_box, text="삭제", width=50, fg_color=DEL_FG, text_color=DEL_TEXT, hover_color=DEL_HOVER, font=FONT_NORMAL, command=lambda n=cat_name: self.delete_category(n)).pack(side="left", padx=5)

        ctk.CTkButton(list_frame, text="+ 새 카테고리 추가", font=FONT_NORMAL, fg_color="transparent", text_color=TEXT_SUB, hover_color=CARD_BG, anchor="w", height=40, command=self.add_category).pack(fill="x", pady=20)

    # --- 2. 갤러리 뷰 ---
    def show_gallery_page(self, container, category_name):
        self.current_category = category_name
        cat_data = self.data["categories"][category_name]

        nav = ctk.CTkFrame(container, fg_color="transparent")
        nav.pack(fill="x", padx=60, pady=(20, 0))
        ctk.CTkButton(nav, text="◀ 목록으로", width=80, fg_color="transparent", text_color=TEXT_SUB, hover_color=CARD_BG, font=FONT_NORMAL, command=lambda: self.switch_frame(self.show_home_page)).pack(side="left")

        theme_text = "🌙 다크" if ctk.get_appearance_mode() == "Light" else "🌞 라이트"
        ctk.CTkButton(nav, text=theme_text, width=80, fg_color=CARD_BG, text_color=TEXT_MAIN, hover_color=HOVER_BG, font=FONT_NORMAL, command=lambda: [self.toggle_theme(), self.switch_frame(self.show_gallery_page, category_name)]).pack(side="right")

        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=60, pady=(10, 10))
        ctk.CTkLabel(header, text=f"📂 {category_name}", font=FONT_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        
        desc_var = tk.StringVar(value=cat_data.get("desc", ""))
        desc_entry = ctk.CTkEntry(header, textvariable=desc_var, font=FONT_NORMAL, text_color=TEXT_SUB, fg_color="transparent", border_width=0, placeholder_text="설명을 입력하세요...")
        desc_entry.pack(fill="x", pady=5)
        def save_desc(e=None):
            cat_data["desc"] = desc_var.get(); self.save_data()
        desc_entry.bind("<FocusOut>", save_desc)
        desc_entry.bind("<Return>", save_desc)

        toolbar = ctk.CTkFrame(container, fg_color="transparent")
        toolbar.pack(fill="x", padx=60, pady=10)

        view_seg = ctk.CTkSegmentedButton(toolbar, values=["갤러리", "리스트"], font=FONT_NORMAL, command=lambda v, c=category_name: self.change_view_mode(v, c), fg_color=HOVER_BG, selected_color="#3B82F6", unselected_color=HOVER_BG, text_color=TEXT_MAIN)
        view_seg.set("갤러리" if self.view_mode == "gallery" else "리스트")
        view_seg.pack(side="left")

        search_entry = ctk.CTkEntry(toolbar, font=FONT_NORMAL, placeholder_text="🔍 제목/태그/내용 통합 검색...", height=32, width=300, fg_color=CARD_BG, text_color=TEXT_MAIN, border_width=1)
        search_entry.pack(side="left", fill="x", expand=True, padx=20)
        search_entry.insert(0, self.search_query)
        search_entry.bind("<KeyRelease>", lambda e: self.apply_filters(search_entry.get()))

        ctk.CTkButton(toolbar, text="+ 프롬프트 작성", fg_color="#3B82F6", text_color="white", hover_color="#2563EB", font=FONT_NORMAL, height=32, command=lambda: self.add_gallery_item(category_name)).pack(side="right")

        self.gallery_scroll_area = ctk.CTkScrollableFrame(container, fg_color="transparent")
        self.gallery_scroll_area.pack(fill="both", expand=True, padx=45, pady=10)

        self.render_filtered_items(category_name)

    def change_view_mode(self, value, category_name):
        self.view_mode = "gallery" if value == "갤러리" else "list"
        self.switch_frame(self.show_gallery_page, category_name)

    def apply_filters(self, search_val):
        self.search_query = search_val
        if self.current_frame and self.current_category:
            for w in self.gallery_scroll_area.winfo_children(): w.destroy()
            self.render_filtered_items(self.current_category)

    def render_filtered_items(self, category_name):
        items = self.data["categories"][category_name].get("items", [])
        filtered = []
        for item in items:
            q = self.search_query.lower()
            
            # 💡 [핵심] 제목, 태그, 프롬프트 내용(fields)까지 싹 다 뒤져서 검색하는 로직 추가!
            match_title = q in item['title'].lower()
            match_tag = any(q in t.lower() for t in item.get("tags", []))
            match_content = any(q in f.get("content", "").lower() for f in item.get("fields", []))
            
            if match_title or match_tag or match_content:
                filtered.append(item)

        if not filtered:
            ctk.CTkLabel(self.gallery_scroll_area, text="조건에 맞는 데이터가 없습니다.", text_color=TEXT_SUB, font=FONT_NORMAL).pack(pady=50)
            return

        if self.view_mode == "gallery": self.render_gallery_view(filtered, category_name)
        else: self.render_list_view(filtered, category_name)

    def render_gallery_view(self, items, category_name):
        grid_frame = ctk.CTkFrame(self.gallery_scroll_area, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True)
        self.current_cards = []

        for item in items:
            card = ctk.CTkFrame(grid_frame, fg_color=CARD_BG, corner_radius=10, width=320, height=280)
            card.grid_propagate(False) 

            thumb_path = item["images"][0] if item.get("images") else ""
            if thumb_path:
                img_lbl = ctk.CTkLabel(card, text="", image=self.load_image_safe(thumb_path, 320, 180), corner_radius=10)
            else:
                img_lbl = ctk.CTkLabel(card, text="이미지 없음", font=FONT_NORMAL, text_color=TEXT_SUB, fg_color=HOVER_BG, width=320, height=180, corner_radius=10)
            img_lbl.pack(fill="x")
            img_lbl.bind("<Button-1>", lambda e, i=item, c=category_name: self.open_detail(c, i, mode="read"))

            title_lbl = ctk.CTkLabel(card, text=f"{item['title']}", font=FONT_SUBTITLE, text_color=TEXT_MAIN, anchor="w")
            title_lbl.pack(fill="x", padx=15, pady=(10, 0))
            title_lbl.bind("<Button-1>", lambda e, i=item, c=category_name: self.open_detail(c, i, mode="read"))

            tag_frame = ctk.CTkFrame(card, fg_color="transparent", height=30)
            tag_frame.pack(fill="x", padx=15, pady=(5, 15))
            tag_frame.pack_propagate(False) 
            for tag in item.get("tags", []):
                if tag.strip():
                    ctk.CTkLabel(tag_frame, text=tag.strip(), font=FONT_TAG, fg_color=HOVER_BG, text_color=TEXT_MAIN, corner_radius=4, padx=8, pady=2).pack(side="left", padx=(0, 5))

            self.current_cards.append(card)

        def on_resize(event):
            w = event.width
            if w < 10: return
            cols = max(1, w // 350)
            if getattr(grid_frame, "current_cols", 0) != cols:
                grid_frame.current_cols = cols
                for i, c in enumerate(self.current_cards):
                    c.grid(row=i//cols, column=i%cols, padx=15, pady=15, sticky="nw")

        self.gallery_scroll_area.bind("<Configure>", on_resize)

    def render_list_view(self, items, category_name):
        for item in items:
            card = ctk.CTkFrame(self.gallery_scroll_area, fg_color=CARD_BG, corner_radius=8, height=50)
            card.pack(fill="x", padx=15, pady=5)
            card.pack_propagate(False) 

            btn = ctk.CTkButton(card, text=f"📄 {item['title']}", font=FONT_SUBTITLE, text_color=TEXT_MAIN, fg_color="transparent", hover_color=HOVER_BG, anchor="w", height=45, command=lambda i=item, c=category_name: self.open_detail(c, i, mode="read"))
            btn.pack(side="left", fill="both", expand=True, padx=10)

            tag_frame = ctk.CTkFrame(card, fg_color="transparent")
            tag_frame.pack(side="right", padx=10, pady=5)
            for tag in item.get("tags", []):
                if tag.strip():
                    ctk.CTkLabel(tag_frame, text=tag.strip(), font=FONT_TAG, fg_color=HOVER_BG, text_color=TEXT_MAIN, corner_radius=4, padx=8, pady=2).pack(side="left", padx=(5, 0))

    # --- 3. 노션 스타일 팝업 ---
    def open_detail(self, category_name, item_data, mode="read"):
        self.field_widgets = [] 
        detail_win = ctk.CTkToplevel(self)
        detail_win.title(item_data['title'])
        detail_win.configure(fg_color=BG_COLOR)
        
        # 💡 [버그 픽스] 강제 최상단 설정 삭제. 파일창 가림 현상 완벽 해결!
        detail_win.transient(self) 
        detail_win.focus_force()

        self.detail_view_mode = "중앙에서 보기"
        center_window(detail_win, self, 850, 850, mode="center")

        view_toolbar = ctk.CTkFrame(detail_win, fg_color="transparent", height=30)
        view_toolbar.pack(fill="x", padx=10, pady=5)
        
        def set_view(choice):
            self.detail_view_mode = choice
            if choice == "사이드 보기": center_window(detail_win, self, 600, 850, mode="side")
            elif choice == "전체 화면": center_window(detail_win, self, 850, 850, mode="full")
            else: center_window(detail_win, self, 850, 850, mode="center")

        view_menu = ctk.CTkOptionMenu(view_toolbar, values=["중앙에서 보기", "사이드 보기", "전체 화면"], font=FONT_NORMAL, command=set_view, fg_color=CARD_BG, text_color=TEXT_MAIN, button_color=CARD_BG, button_hover_color=HOVER_BG)
        view_menu.set("중앙에서 보기")
        view_menu.pack(side="left")

        scroll = ctk.CTkScrollableFrame(detail_win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=40, pady=(0, 20))

        if mode == "read": self.build_read_mode(scroll, detail_win, category_name, item_data)
        else: self.build_edit_mode(scroll, detail_win, category_name, item_data)

    def render_notion_properties(self, parent, item_data, is_edit_mode):
        prop_frame = ctk.CTkFrame(parent, fg_color="transparent")
        prop_frame.pack(fill="x", pady=(0, 20), padx=5)

        row1 = ctk.CTkFrame(prop_frame, fg_color="transparent")
        row1.pack(fill="x", pady=4)
        ctk.CTkLabel(row1, text="이미지", font=FONT_NORMAL, text_color=TEXT_SUB, width=100, anchor="w").pack(side="left")
        
        images = item_data.get("images", [])
        if is_edit_mode:
            img_container = ctk.CTkFrame(row1, fg_color="transparent")
            img_container.pack(side="left", fill="x", expand=True)
            self.temp_images = list(images)
            self.render_image_manager(img_container, self.temp_images)
        else:
            if images: ctk.CTkLabel(row1, text=f"{len(images)}개의 파일", font=FONT_NORMAL, text_color=TEXT_MAIN).pack(side="left")
            else: ctk.CTkLabel(row1, text="비어 있음", font=FONT_NORMAL, text_color=TEXT_SUB).pack(side="left")

        row2 = ctk.CTkFrame(prop_frame, fg_color="transparent")
        row2.pack(fill="x", pady=4)
        ctk.CTkLabel(row2, text="태그", font=FONT_NORMAL, text_color=TEXT_SUB, width=100, anchor="w").pack(side="left")
        
        if is_edit_mode:
            self.temp_tags = list(item_data.get('tags', []))
            tag_wrapper = ctk.CTkFrame(row2, fg_color="transparent")
            tag_wrapper.pack(side="left", fill="x", expand=True)
            tag_badges_frame = ctk.CTkScrollableFrame(tag_wrapper, orientation="horizontal", height=45, fg_color="transparent")
            tag_badges_frame.pack(fill="x")

            def render_tags():
                for w in tag_badges_frame.winfo_children(): w.destroy()
                for t in self.temp_tags:
                    tf = ctk.CTkFrame(tag_badges_frame, fg_color=HOVER_BG, corner_radius=4)
                    tf.pack(side="left", padx=(0, 8), pady=2)
                    ctk.CTkLabel(tf, text=t, font=FONT_TAG, text_color=TEXT_MAIN).pack(side="left", padx=(8, 2))
                    ctk.CTkButton(tf, text="x", width=20, height=20, fg_color="transparent", text_color=DEL_TEXT, hover_color=DEL_HOVER, font=("Arial", 12, "bold"), command=lambda tag=t: remove_tag(tag)).pack(side="left", padx=(0, 2))

            def remove_tag(tag):
                if tag in self.temp_tags: self.temp_tags.remove(tag)
                render_tags()

            def on_tag_enter(event):
                val = self.tag_entry.get().strip()
                if val and val not in self.temp_tags:
                    self.temp_tags.append(val)
                    self.tag_entry.delete(0, "end")
                    render_tags()

            self.tag_entry = ctk.CTkEntry(tag_wrapper, font=FONT_NORMAL, text_color=TEXT_MAIN, fg_color="transparent", border_width=0, placeholder_text="입력 후 Enter...")
            self.tag_entry.pack(fill="x")
            self.tag_entry.bind("<Return>", on_tag_enter)
            render_tags()
        else:
            if item_data.get('tags'):
                tag_frame = ctk.CTkFrame(row2, fg_color="transparent")
                tag_frame.pack(side="left")
                for tag in item_data.get('tags', []):
                    if tag.strip(): ctk.CTkLabel(tag_frame, text=tag.strip(), font=FONT_TAG, fg_color=HOVER_BG, text_color=TEXT_MAIN, corner_radius=4, padx=8, pady=2).pack(side="left", padx=(0, 5))
            else: ctk.CTkLabel(row2, text="비어 있음", font=FONT_NORMAL, text_color=TEXT_SUB).pack(side="left")

        sep = ctk.CTkFrame(parent, fg_color=HOVER_BG, height=1)
        sep.pack(fill="x", pady=(10, 20))

    def apply_syntax_highlighting(self, tk_text):
        content = tk_text.get("1.0", "end-1c")
        for tag in ["number", "bracket", "colon"]: tk_text.tag_remove(tag, "1.0", "end")
            
        tk_text.tag_config("number", foreground="#FF5252") 
        tk_text.tag_config("bracket", foreground="#448AFF") 
        tk_text.tag_config("colon", foreground="#9CA3AF") 

        for match in re.finditer(r'\b\d+(\.\d+)?\b', content): tk_text.tag_add("number", f"1.0+{match.start()}c", f"1.0+{match.end()}c")
        for match in re.finditer(r'[\(\)\[\]\{\}]', content): tk_text.tag_add("bracket", f"1.0+{match.start()}c", f"1.0+{match.end()}c")
        for match in re.finditer(r'::?|,', content): tk_text.tag_add("colon", f"1.0+{match.start()}c", f"1.0+{match.end()}c")

    def build_read_mode(self, scroll, detail_win, category_name, item_data):
        toolbar = ctk.CTkFrame(scroll, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(toolbar, text="수정하기", width=80, fg_color=HOVER_BG, text_color=TEXT_MAIN, hover_color=CARD_BG, font=FONT_NORMAL, command=lambda: [detail_win.destroy(), self.open_detail(category_name, item_data, "edit")]).pack(side="right", padx=5)
        
        ctk.CTkLabel(scroll, text=item_data['title'], font=FONT_TITLE, text_color=TEXT_MAIN, anchor="w").pack(fill="x", pady=(10, 15))
        self.render_notion_properties(scroll, item_data, is_edit_mode=False)

        images = item_data.get("images", [])
        if images:
            img_container = ctk.CTkFrame(scroll, fg_color="transparent")
            img_container.pack(fill="x", pady=(0, 20))
            for img_path in images:
                ctk.CTkLabel(img_container, text="", image=self.load_image_safe(img_path, 700, 400), corner_radius=10).pack(pady=10)

        for field in item_data.get("fields", []):
            content = field.get("content", "").strip()
            if content: self.create_readonly_box(scroll, field.get("title", "내용"), content, field.get("height", 150))

    def create_readonly_box(self, parent, label, content, height):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", pady=(15, 5))
        ctk.CTkLabel(header, text=label, font=FONT_SUBTITLE, text_color=TEXT_MAIN).pack(side="left")
        ctk.CTkButton(header, text="복사", width=50, height=25, fg_color=HOVER_BG, text_color=TEXT_MAIN, hover_color=CARD_BG, font=FONT_NORMAL, command=lambda: self.copy_to_clipboard(content)).pack(side="right")
        
        box = ctk.CTkTextbox(parent, height=height, fg_color=CODE_BG, text_color=TEXT_MAIN, font=FONT_PROMPT, border_width=0, corner_radius=8, wrap="word")
        box.pack(fill="x")
        box.insert("1.0", content)
        self.apply_syntax_highlighting(box._textbox)
        box.configure(state="disabled")

    def build_edit_mode(self, scroll, detail_win, category_name, item_data):
        toolbar = ctk.CTkFrame(scroll, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(toolbar, text="이 항목 삭제", fg_color=DEL_FG, text_color=DEL_TEXT, hover_color=DEL_HOVER, font=FONT_NORMAL, command=lambda: self.delete_gallery_item(detail_win, category_name, item_data)).pack(side="right")

        title_var = tk.StringVar(value=item_data['title'] if item_data['title'] != "제목 없음" else "")
        title_entry = ctk.CTkEntry(scroll, textvariable=title_var, font=FONT_TITLE, text_color=TEXT_MAIN, fg_color="transparent", border_width=0, height=50, placeholder_text="제목을 입력하세요")
        title_entry.pack(fill="x", pady=(5, 15))
        
        if not title_var.get(): detail_win.after(100, title_entry.focus)

        self.render_notion_properties(scroll, item_data, is_edit_mode=True)

        fields_container = ctk.CTkFrame(scroll, fg_color="transparent")
        fields_container.pack(fill="x", pady=(15, 5))
        
        for field_data in item_data.get("fields", []):
            self.add_field_ui(fields_container, field_data)
            
        ctk.CTkButton(scroll, text="+ 항목 추가", fg_color="transparent", text_color=TEXT_SUB, hover_color=HOVER_BG, font=FONT_NORMAL, height=40, command=lambda: self.add_field_ui(fields_container, {"title": "", "content": "", "height": 150})).pack(fill="x", pady=10)

        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=30)
        ctk.CTkButton(btn_frame, text="취소", fg_color=HOVER_BG, text_color=TEXT_MAIN, hover_color=CARD_BG, font=FONT_NORMAL, height=45, command=lambda: [detail_win.destroy(), self.open_detail(category_name, item_data, "read")]).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="저장 완료", fg_color="#3B82F6", text_color="white", hover_color="#2563EB", font=FONT_NORMAL, height=45, command=lambda: self.save_item_changes(category_name, item_data, title_var.get(), self.temp_images, detail_win)).pack(side="right", padx=5)

    def add_field_ui(self, container, field_data):
        frame = ctk.CTkFrame(container, fg_color="transparent")
        frame.pack(fill="x", pady=10)

        top_row = ctk.CTkFrame(frame, fg_color="transparent")
        top_row.pack(fill="x", pady=(10, 5))

        title_var = tk.StringVar(value=field_data.get("title", ""))
        
        # 💡 [버그 픽스] 눈에 안 띄던 제목 입력칸에 확실한 테두리와 가이드 텍스트 부여
        title_entry = ctk.CTkEntry(top_row, textvariable=title_var, font=FONT_SUBTITLE, fg_color=CARD_BG, text_color=TEXT_MAIN, border_width=1, border_color="#E5E7EB", placeholder_text="항목의 제목을 입력하세요 (예: 프롬프트, 네거티브)")
        title_entry.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(top_row, text="삭제", width=50, fg_color=DEL_FG, text_color=DEL_TEXT, hover_color=DEL_HOVER, command=lambda: self.remove_field_ui(frame, widget_tuple)).pack(side="right", padx=(10, 0))

        height_var = tk.IntVar(value=field_data.get("height", 150))
        box = ctk.CTkTextbox(frame, height=height_var.get(), fg_color=CODE_BG, text_color=TEXT_MAIN, font=FONT_PROMPT, border_width=0, corner_radius=8, wrap="word")
        box.pack(fill="x", pady=(5, 0))
        box.insert("1.0", field_data.get("content", ""))
        
        self.apply_syntax_highlighting(box._textbox)
        box._textbox.bind("<KeyRelease>", lambda e: self.apply_syntax_highlighting(box._textbox))

        grip = ctk.CTkLabel(frame, text="⇲ ", cursor="sizing", text_color="#9CA3AF", font=("Arial", 16))
        grip.pack(side="bottom", anchor="e", padx=5)

        def on_drag(event):
            dy = event.y_root - grip.start_y
            new_h = max(50, height_var.get() + dy)
            box.configure(height=new_h)
            grip.last_h = new_h

        def on_press(event):
            grip.start_y = event.y_root
            grip.last_h = height_var.get()
            
        def on_release(event): height_var.set(grip.last_h)

        grip.bind("<ButtonPress-1>", on_press)
        grip.bind("<B1-Motion>", on_drag)
        grip.bind("<ButtonRelease-1>", on_release)

        widget_tuple = (title_var, box, height_var, frame)
        self.field_widgets.append(widget_tuple)

    def remove_field_ui(self, frame, widget_tuple):
        frame.destroy()
        if widget_tuple in self.field_widgets: self.field_widgets.remove(widget_tuple)

    def render_image_manager(self, container, image_list):
        for widget in container.winfo_children(): widget.destroy()
        info_frame = ctk.CTkFrame(container, fg_color="transparent")
        info_frame.pack(fill="x", pady=2)
        ctk.CTkButton(info_frame, text="+ 첨부", fg_color=HOVER_BG, text_color=TEXT_MAIN, hover_color=CARD_BG, font=FONT_NORMAL, height=30, width=60, command=lambda: self.add_img(container, image_list)).pack(side="left")

        if image_list:
            scroll_img = ctk.CTkScrollableFrame(container, orientation="horizontal", height=100, fg_color="transparent")
            scroll_img.pack(fill="x", pady=5)
            for idx, img_path in enumerate(image_list):
                row_frame = ctk.CTkFrame(scroll_img, fg_color="transparent")
                row_frame.pack(side="left", padx=5)
                ctk.CTkLabel(row_frame, text="", image=self.load_image_safe(img_path, 100, 70), corner_radius=8).pack(pady=2)
                btn_box = ctk.CTkFrame(row_frame, fg_color="transparent")
                btn_box.pack()
                ctk.CTkButton(btn_box, text="◀", width=25, height=20, fg_color="transparent", text_color=TEXT_SUB, hover_color=HOVER_BG, command=lambda i=idx: self.move_img(container, image_list, i, -1)).pack(side="left")
                ctk.CTkButton(btn_box, text="▶", width=25, height=20, fg_color="transparent", text_color=TEXT_SUB, hover_color=HOVER_BG, command=lambda i=idx: self.move_img(container, image_list, i, 1)).pack(side="left")
                ctk.CTkButton(btn_box, text="x", width=25, height=20, fg_color="transparent", text_color=DEL_TEXT, hover_color=DEL_FG, command=lambda i=idx: self.del_img(container, image_list, i)).pack(side="left")

    def move_img(self, c, l, i, d):
        if 0 <= i + d < len(l):
            l.insert(i + d, l.pop(i))
            self.render_image_manager(c, l)
            
    def del_img(self, c, l, i):
        l.pop(i)
        self.render_image_manager(c, l)
    
    def add_img(self, c, l):
        files = filedialog.askopenfilenames(title="이미지 선택", filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp")])
        for f in files:
            ext = os.path.splitext(f)[1]
            dest = os.path.join(IMG_FOLDER, f"{uuid.uuid4().hex}{ext}")
            try: shutil.copy(f, dest); l.append(dest)
            except Exception: pass
        self.render_image_manager(c, l)

    def copy_to_clipboard(self, text):
        self.clipboard_clear(); self.clipboard_append(text); self.update()
        messagebox.showinfo("알림", "복사 완료!", parent=self)

    def edit_main_title(self):
        dialog = CustomDialog(self, "이름 수정", "갤러리의 새로운 이름을 입력하세요:", initial_name=self.data["title"])
        if dialog.result_name:
            self.data["title"] = dialog.result_name
            self.save_data()
            self.switch_frame(self.show_home_page)

    def add_category(self):
        dialog = CustomDialog(self, "카테고리 추가", "새 카테고리 이름을 입력하세요:")
        if dialog.result_name:
            if dialog.result_name in self.data["categories"]: return messagebox.showerror("에러", "이미 존재하는 카테고리입니다.", parent=self)
            self.data["categories"][dialog.result_name] = {"items": [], "desc": ""}
            self.save_data()
            self.switch_frame(self.show_home_page)

    def edit_category(self, old_name):
        dialog = CustomDialog(self, "카테고리 수정", "카테고리의 새 이름을 입력하세요:", initial_name=old_name)
        if dialog.result_name:
            new_name = dialog.result_name
            if new_name != old_name and new_name in self.data["categories"]: return messagebox.showerror("에러", "이미 존재하는 카테고리입니다.", parent=self)
            new_categories = {}
            for k, v in self.data["categories"].items():
                if k == old_name: new_categories[new_name] = v
                else: new_categories[k] = v
            self.data["categories"] = new_categories
            self.save_data()
            self.switch_frame(self.show_home_page)

    def delete_category(self, cat_name):
        if messagebox.askyesno("삭제", f"'{cat_name}' 카테고리를 삭제하시겠습니까?", parent=self):
            del self.data["categories"][cat_name]
            self.save_data(); self.switch_frame(self.show_home_page)

    def add_gallery_item(self, category_name):
        new_item = {
            "id": str(uuid.uuid4()),
            "title": "제목 없음",
            "images": [],
            "tags": [],
            "fields": [{"title": "프롬프트", "content": "", "height": 150}]
        }
        self.data["categories"][category_name]["items"].insert(0, new_item)
        self.save_data()
        self.apply_filters("") 
        self.open_detail(category_name, new_item, mode="edit")

    def save_item_changes(self, cat, item, title, imgs, win):
        item["title"] = title if title.strip() else "제목 없음"
        item["tags"] = list(self.temp_tags) 
        item["images"] = imgs
        new_fields = []
        for t_var, box, h_var, _ in self.field_widgets:
            new_fields.append({
                "title": t_var.get().strip() or "내용",
                "content": box.get("1.0", "end-1c").strip(),
                "height": h_var.get()
            })
        item["fields"] = new_fields
        self.save_data()
        self.apply_filters(self.search_query) 
        win.destroy()

    def delete_gallery_item(self, win, cat, item):
        if messagebox.askyesno("삭제", "이 프롬프트를 삭제하시겠습니까?", parent=win):
            self.data["categories"][cat]["items"] = [x for x in self.data["categories"][cat]["items"] if x.get("id") != item.get("id")]
            self.save_data()
            self.apply_filters(self.search_query)
            win.destroy()

if __name__ == "__main__":
    app = NotionGalleryApp()
    app.mainloop()