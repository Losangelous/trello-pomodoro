#本.py文件用于切换深色/浅色模式
import flet as ft

class DarkTheme:
    def __init__(self,page:ft.Page):
        self.page=page
        self.page.theme_mode=ft.ThemeMode.LIGHT
        self._setup_themes()

    def _setup_themes(self):
        self.page.theme=ft.Theme(color_scheme_seed=ft.Colors.BLUE)
        self.page.dark_theme=ft.Theme(color_scheme_seed=ft.Colors.BLUE)

    def toggle(self,e):
        if self.page.theme_mode==ft.ThemeMode.LIGHT:
            self.page.theme_mode=ft.ThemeMode.DARK
            e.control.text="浅色模式"
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            e.control.text = "深色模式"
        if hasattr(self.page,'board_view'):
            self.page.board_view.refresh_by_theme()
        self.page.update()

    def get_button(self):
        return ft.ElevatedButton(text="深色模式",on_click=self.toggle)
    
   