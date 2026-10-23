"""
Ứng dụng Study Tracker Dashboard v2.0 (Terminal UI)
Sử dụng thư viện Textual trong Python
Tính năng:
1. Lưu trữ dữ liệu vĩnh viễn với tệp CSV (study_history.csv)
2. Tự động chặn và bỏ chặn web xao nhãng (/etc/hosts)
3. Âm thanh chuông paplay và thông báo notify-send bất đồng bộ
4. Tách biệt chế độ Test nhanh (Phím T) không ghi dữ liệu vào CSV/thống kê
5. Tính năng xóa dòng nhật ký đã chọn (Phím D hoặc Delete)
"""

import atexit
import csv
from datetime import datetime
from pathlib import Path
import re
import signal
import subprocess
import sys

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Digits,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    Static,
)

# Đường dẫn tệp dữ liệu CSV lưu trữ nhật ký học tập
CSV_FILE_PATH = Path(__file__).resolve().parent / "study_history.csv"

# Cấu hình danh sách chặn trang web xao nhãng qua /etc/hosts
HOSTS_FILE_PATH = Path("/etc/hosts")
BLOCK_START_MARKER = "# START_STUDY_BLOCK"
BLOCK_END_MARKER = "# END_STUDY_BLOCK"

BLOCKED_DOMAINS = [
    "facebook.com",
    "www.facebook.com",
    "youtube.com",
    "www.youtube.com",
    "tiktok.com",
    "www.tiktok.com",
]


def block_distractions(hosts_path: Path = HOSTS_FILE_PATH) -> bool:
    """Thêm khối chặn các tên miền gây xao nhãng vào tệp hosts (trỏ về 127.0.0.1)."""
    try:
        if not hosts_path.exists():
            return False
        content = hosts_path.read_text(encoding="utf-8")
        if BLOCK_START_MARKER in content:
            return True  # Đã có khối chặn

        block_lines = [
            BLOCK_START_MARKER,
            *(f"127.0.0.1 {domain}" for domain in BLOCKED_DOMAINS),
            BLOCK_END_MARKER,
        ]
        new_content = content.rstrip() + "\n\n" + "\n".join(block_lines) + "\n"
        hosts_path.write_text(new_content, encoding="utf-8")
        return True
    except (OSError, PermissionError):
        return False


def unblock_distractions(hosts_path: Path = HOSTS_FILE_PATH) -> bool:
    """Lọc bỏ hoàn toàn khối chặn giữa START_STUDY_BLOCK và END_STUDY_BLOCK khỏi tệp hosts."""
    try:
        if not hosts_path.exists():
            return False
        content = hosts_path.read_text(encoding="utf-8")
        if BLOCK_START_MARKER not in content:
            return True  # Không có khối chặn cần gỡ

        pattern = re.compile(
            rf"\n?{re.escape(BLOCK_START_MARKER)}.*?{re.escape(BLOCK_END_MARKER)}\n?",
            re.DOTALL,
        )
        new_content = pattern.sub("\n", content).rstrip() + "\n"
        hosts_path.write_text(new_content, encoding="utf-8")
        return True
    except (OSError, PermissionError):
        return False


# Đảm bảo tự động khôi phục /etc/hosts khi thoát chương trình bằng atexit
atexit.register(unblock_distractions)


APP_CSS = """
Screen {
    background: #1e1e2e;
    color: #cdd6f4;
}

#main-container {
    padding: 0 1;
    height: 100%;
}

/* Ô nhập liệu môn học */
#input-panel {
    background: #181825;
    border: round #45475a;
    padding: 0 1;
    margin-bottom: 0;
    height: auto;
}

#input-label {
    color: #89b4fa;
    text-style: bold;
}

#subject-input {
    background: #1e1e2e;
    border: tall #313244;
    color: #cdd6f4;
    height: 3;
}

#subject-input:focus {
    border: tall #89b4fa;
}

/* Khối Timer và Thống kê */
#middle-panel {
    height: auto;
    margin-bottom: 0;
}

#timer-card {
    background: #181825;
    border: round #89b4fa;
    padding: 0 1;
    width: 60%;
    height: auto;
    align: center middle;
}

#timer-card.mode-break-card {
    border: round #a6e3a1;
}

#timer-badge {
    text-align: center;
    text-style: bold;
    color: #89b4fa;
}

#timer-badge.mode-break-badge {
    color: #a6e3a1;
}

#timer-digits {
    text-align: center;
    color: #cdd6f4;
    margin: 0;
}

#timer-progress {
    width: 100%;
    margin-bottom: 0;
}

#timer-button-row {
    width: 100%;
    align: center middle;
    height: auto;
}

#timer-button-row Button {
    margin: 0 1;
    min-width: 11;
}

/* Thẻ thống kê bên phải */
#stats-card {
    background: #181825;
    border: round #45475a;
    padding: 0 1;
    width: 40%;
    margin-left: 1;
    height: auto;
}

#stats-title {
    text-style: bold;
    color: #fab387;
    border-bottom: solid #313244;
    margin-bottom: 0;
}

.stat-row {
    margin-bottom: 0;
}

#stats-instructions {
    margin-top: 0;
    padding-top: 0;
    border-top: dashed #313244;
    color: #a6adc8;
}

/* Khối Nhật ký học tập (DataTable) */
#log-panel {
    background: #181825;
    border: round #45475a;
    padding: 0 1;
    height: 1fr;
    min-height: 8;
}

#log-header-bar {
    height: auto;
    width: 100%;
    align: right middle;
    margin-bottom: 0;
}

#log-title {
    text-style: bold;
    color: #a6e3a1;
    width: 1fr;
    content-align: left middle;
}

#btn-delete-log {
    min-width: 24;
    height: 1;
    border: none;
    background: #f38ba8;
    color: #11111b;
    text-style: bold;
    padding: 0 1;
}

#btn-delete-log:hover {
    background: #eba0ac;
}

#log-table {
    height: 1fr;
    background: #181825;
}

#log-table > .datatable--header {
    background: #313244;
    color: #89b4fa;
    text-style: bold;
}
"""


class StudyDashboardApp(App):
    """Ứng dụng Dashboard Quản lý học tập và Pomodoro Timer trên Terminal (v2.0)."""

    TITLE = "STUDY TRACKER - TERMINAL DASHBOARD"
    SUB_TITLE = "v2.0"
    CSS = APP_CSS

    BINDINGS = [
        Binding("space", "toggle_timer", "Bắt đầu / Tạm dừng", show=True),
        Binding("r", "reset_timer", "Đặt lại (Reset)", show=True),
        Binding("m", "toggle_mode", "Đổi chế độ Học/Nghỉ", show=True),
        Binding("t", "test_complete", "Test chuông & nghỉ", show=True),
        Binding("d", "delete_selected_log", "Xóa phiên chọn", show=True),
        Binding("delete", "delete_selected_log", "Xóa phiên chọn", show=False),
        Binding("q", "quit_app", "Thoát", show=True),
    ]

    def __init__(self, hosts_path: Path = HOSTS_FILE_PATH, csv_path: Path = CSV_FILE_PATH):
        super().__init__()
        self.hosts_path = hosts_path
        self.csv_path = csv_path

        # Cấu hình thời gian mặc định (tính theo giây)
        self.WORK_DURATION: int = 25 * 60  # 25 phút học
        self.BREAK_DURATION: int = 5 * 60  # 5 phút nghỉ giải lao

        # Biến trạng thái Pomodoro
        self.pomo_mode: str = "work"  # 'work' hoặc 'break'
        self.pomo_seconds_left: int = self.WORK_DURATION
        self.pomo_running: bool = False
        self.pomo_timer = None

        # Trạng thái chặn web
        self.is_blocking_active: bool = False

        # Thống kê
        self.completed_pomodoros: int = 0
        self.total_focus_minutes: int = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="main-container"):
            # 1. Ô nhập liệu Môn học / Mục tiêu
            with Container(id="input-panel"):
                yield Label("🎯 Môn học / Mục tiêu phiên học hiện tại:", id="input-label")
                yield Input(
                    value="Ôn tập Vật lý chuyên đề Dao động",
                    placeholder="Gõ tên môn học hoặc mục tiêu cần hoàn thành...",
                    id="subject-input",
                )

            # 2. Hàng giữa: Đồng hồ Pomodoro và Bảng thống kê
            with Horizontal(id="middle-panel"):
                # Cột trái: Pomodoro Card
                with Vertical(id="timer-card"):
                    yield Label("🎯 ĐANG TRONG PHIÊN HỌC TẬP (25 PHÚT)", id="timer-badge")
                    yield Digits("25:00", id="timer-digits")
                    yield ProgressBar(
                        total=self.WORK_DURATION,
                        id="timer-progress",
                        show_eta=False,
                    )
                    with Horizontal(id="timer-button-row"):
                        yield Button("▶ Bắt đầu", id="btn-start", variant="success")
                        yield Button("⏸ Tạm dừng", id="btn-pause", variant="warning")
                        yield Button("🔄 Đặt lại", id="btn-reset", variant="error")
                        yield Button("☕ Chuyển sang Nghỉ", id="btn-toggle-mode", variant="primary")

                # Cột phải: Thẻ thống kê & Phím tắt
                with Vertical(id="stats-card"):
                    yield Label("📊 THỐNG KÊ PHIÊN HỌC", id="stats-title")
                    yield Label("• Phiên hoàn thành : [bold cyan]0 phiên[/bold cyan]", id="stat-sessions", classes="stat-row")
                    yield Label("• Thời gian học   : [bold green]0 phút[/bold green]", id="stat-time", classes="stat-row")
                    yield Label("• Trạng thái      : [bold yellow]Sẵn sàng[/bold yellow]", id="stat-status", classes="stat-row")
                    yield Label("• Chặn web xao nhãng: [dim]ĐÃ TẮT 🌐[/dim]", id="stat-blocker", classes="stat-row")
                    
                    with Static(id="stats-instructions"):
                        yield Label(
                            "[dim]Phím tắt:[/dim] [bold cyan]Space[/bold cyan]: Chạy/Dừng | [bold cyan]R[/bold cyan]: Đặt lại | [bold cyan]M[/bold cyan]: Đổi chế độ\n"
                            "• [bold cyan]T[/bold cyan]: Test chuông & nghỉ (Không lưu) | [bold cyan]D[/bold cyan]: Xóa phiên đã chọn\n"
                            "• [bold cyan]Q[/bold cyan]: Thoát ứng dụng (Khôi phục mạng)"
                        )

            # 3. Hàng dưới: Bảng nhật ký học tập (Study Log)
            with Vertical(id="log-panel"):
                with Horizontal(id="log-header-bar"):
                    yield Label("📋 NHẬT KÝ HỌC TẬP (STUDY LOG) — CSV PERSISTENT", id="log-title")
                    yield Button("🗑️ Xóa phiên đã chọn (Phím D)", id="btn-delete-log", variant="error")
                yield DataTable(id="log-table", zebra_stripes=True, cursor_type="row")

        yield Footer()

    def on_mount(self) -> None:
        """Khởi tạo ứng dụng: tạo cột bảng, tải dữ liệu từ CSV và thiết lập timer."""
        # Đảm bảo unblock /etc/hosts khi mới khởi động ứng dụng
        unblock_distractions(self.hosts_path)
        self.is_blocking_active = False

        table = self.query_one("#log-table", DataTable)
        table.add_columns(
            "STT",
            "Thời gian hoàn thành",
            "Môn học / Mục tiêu",
            "Thời lượng",
            "Trạng thái",
        )

        # Nạp dữ liệu lịch sử từ tệp CSV
        self.load_history_from_csv()

        # Thiết lập interval 1 giây (ở trạng thái tạm dừng ban đầu)
        self.pomo_timer = self.set_interval(1.0, self.on_timer_tick, pause=True)
        self.update_timer_display()
        self.update_stats_panel()

    def on_unmount(self) -> None:
        """Đảm bảo gỡ bỏ hoàn toàn chặn web khi đóng ứng dụng."""
        unblock_distractions(self.hosts_path)
        self.is_blocking_active = False

    # --- Quản lý dữ liệu CSV (Persistence) ---

    def ensure_csv_file(self) -> None:
        """Đảm bảo tệp CSV tồn tại kèm theo dòng tiêu đề (Header)."""
        if not self.csv_path.exists():
            try:
                with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["STT", "ThoiGian", "MonHoc", "ThoiLuong", "TrangThai"])
            except Exception as e:
                self.notify(f"Không thể tạo tệp CSV: {e}", severity="error")

    def load_history_from_csv(self) -> None:
        """Tự động nạp toàn bộ lịch sử từ file CSV vào bảng và cập nhật thống kê."""
        self.ensure_csv_file()
        table = self.query_one("#log-table", DataTable)
        table.clear()

        self.completed_pomodoros = 0
        self.total_focus_minutes = 0

        if not self.csv_path.exists():
            return

        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)  # Bỏ qua dòng tiêu đề

                for row in reader:
                    if not row or len(row) < 5:
                        continue
                    stt, time_str, subject, duration, status = row[0], row[1], row[2], row[3], row[4]
                    table.add_row(stt, time_str, subject, duration, status)
                    self.completed_pomodoros += 1

                    # Trích xuất số phút học từ cột ThoiLuong
                    digits = "".join(ch for ch in duration if ch.isdigit())
                    minutes = int(digits) if digits else 25
                    self.total_focus_minutes += minutes

            if len(table.rows) > 0:
                table.scroll_end(animate=False)
        except Exception as e:
            self.notify(f"Lỗi khi đọc file CSV: {e}", severity="warning")

    def append_session_to_csv(self, stt: str, timestamp_str: str, subject_name: str, duration: str, status: str) -> bool:
        """Ghi thêm một dòng phiên học mới vào tệp CSV."""
        self.ensure_csv_file()
        try:
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([stt, timestamp_str, subject_name, duration, status])
            return True
        except Exception as e:
            self.notify(f"Không thể ghi nhật ký vào CSV: {e}", severity="error")
            return False

    def delete_selected_log(self) -> None:
        """Xóa dòng nhật ký đang được chọn trên bảng DataTable và tệp CSV."""
        table = self.query_one("#log-table", DataTable)
        if not table.rows:
            self.notify("Bảng nhật ký đang trống, không có dòng để xóa.", title="Thông báo", severity="warning", timeout=3)
            return

        cursor_row = table.cursor_row
        if cursor_row is None or cursor_row < 0 or cursor_row >= len(table.rows):
            self.notify("Vui lòng dùng phím mũi tên hoặc chuột chọn một dòng trên bảng để xóa.", title="Chưa chọn dòng", severity="warning", timeout=3)
            return

        if not self.csv_path.exists():
            self.notify("Không tìm thấy tệp CSV nhật ký.", severity="error", timeout=3)
            return

        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                rows = list(reader)

            if not (0 <= cursor_row < len(rows)):
                self.notify("Vị trí dòng chọn không hợp lệ.", severity="error", timeout=3)
                return

            deleted_row = rows.pop(cursor_row)
            deleted_subject = deleted_row[2] if len(deleted_row) > 2 else "Phiên học"
            deleted_stt = deleted_row[0] if len(deleted_row) > 0 else str(cursor_row + 1)

            # Đánh số lại STT cho các dòng còn lại
            for idx, r in enumerate(rows, start=1):
                if len(r) > 0:
                    r[0] = str(idx)

            # Ghi lại danh sách mới vào tệp CSV
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(header or ["STT", "ThoiGian", "MonHoc", "ThoiLuong", "TrangThai"])
                writer.writerows(rows)

            # Nạp lại bảng và cập nhật khung Thống kê
            self.load_history_from_csv()

            # Điều chỉnh vị trí con trỏ sau khi xóa
            if rows:
                new_cursor = min(cursor_row, len(rows) - 1)
                table.move_cursor(row=new_cursor)

            self.notify(
                f"Đã xóa phiên: {deleted_subject} (#{deleted_stt}) khỏi nhật ký.",
                title="🗑️ Đã xóa phiên học",
                severity="warning",
                timeout=4,
            )
        except Exception as e:
            self.notify(f"Lỗi khi xóa dòng nhật ký: {e}", severity="error", timeout=4)

    # --- Quản lý chặn web (/etc/hosts) ---

    def activate_web_blocker(self) -> None:
        """Bật chặn các trang web xao nhãng."""
        success = block_distractions(self.hosts_path)
        self.is_blocking_active = success
        self.update_stats_panel()
        if success:
            self.notify(
                "Đã chặn Facebook, Youtube, TikTok trong /etc/hosts!",
                title="🛡️ Chế độ tập trung cao độ",
                severity="information",
                timeout=4,
            )

    def deactivate_web_blocker(self) -> None:
        """Gỡ bỏ chặn các trang web xao nhãng, khôi phục mạng bình thường."""
        unblock_distractions(self.hosts_path)
        self.is_blocking_active = False
        self.update_stats_panel()

    # --- Xử lý sự kiện Timer ---

    def on_timer_tick(self) -> None:
        """Được gọi mỗi giây khi Pomodoro đang chạy."""
        if self.pomo_seconds_left > 0:
            self.pomo_seconds_left -= 1
            self.update_timer_display()
        else:
            # Hết thời gian phiên đếm ngược thực tế (chạy đủ 25 phút về 00:00)
            self.on_session_finished()

    def update_timer_display(self) -> None:
        """Cập nhật giao diện đồng hồ Digits và thanh tiến trình ProgressBar."""
        minutes = self.pomo_seconds_left // 60
        seconds = self.pomo_seconds_left % 60
        self.query_one("#timer-digits", Digits).update(f"{minutes:02d}:{seconds:02d}")

        # Tính toán thanh tiến trình
        total = self.WORK_DURATION if self.pomo_mode == "work" else self.BREAK_DURATION
        elapsed = total - self.pomo_seconds_left
        progress_bar = self.query_one("#timer-progress", ProgressBar)
        progress_bar.total = total
        progress_bar.progress = elapsed

    def update_stats_panel(self) -> None:
        """Cập nhật các chỉ số trong thẻ thống kê."""
        self.query_one("#stat-sessions", Label).update(
            f"• Phiên hoàn thành : [bold cyan]{self.completed_pomodoros} phiên[/bold cyan]"
        )
        self.query_one("#stat-time", Label).update(
            f"• Thời gian học   : [bold green]{self.total_focus_minutes} phút[/bold green]"
        )

        if not self.pomo_running:
            status_text = "[bold yellow]Đang tạm dừng[/bold yellow]" if self.pomo_seconds_left < (
                self.WORK_DURATION if self.pomo_mode == "work" else self.BREAK_DURATION
            ) else "[bold yellow]Sẵn sàng[/bold yellow]"
        else:
            status_text = (
                "[bold cyan]⚡ Đang tập trung...[/bold cyan]"
                if self.pomo_mode == "work"
                else "[bold green]☕ Đang nghỉ ngơi...[/bold green]"
            )

        self.query_one("#stat-status", Label).update(f"• Trạng thái      : {status_text}")

        # Cập nhật trạng thái Chặn Web
        blocker_text = (
            "[bold green]ĐANG BẬT 🛡️ (127.0.0.1)[/bold green]"
            if self.is_blocking_active
            else "[dim]ĐÃ TẮT 🌐 (Bình thường)[/dim]"
        )
        self.query_one("#stat-blocker", Label).update(f"• Chặn web xao nhãng: {blocker_text}")

    def play_session_alerts(self) -> None:
        """Phát âm thanh hệ thống và gửi desktop notification không đồng bộ (non-blocking)."""
        self.bell()  # Chuông dự phòng của terminal

        # 1. Phát chuông hệ thống Linux qua lệnh paplay ngầm
        try:
            subprocess.Popen(
                ["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            try:
                subprocess.Popen(
                    "paplay /usr/share/sounds/freedesktop/stereo/complete.oga &",
                    shell=True,
                )
            except Exception:
                pass

        # 2. Bắn thông báo nổi lên góc màn hình Desktop qua notify-send ngầm
        try:
            subprocess.Popen(
                [
                    "notify-send",
                    "-i",
                    "accessories-calculator",
                    "Pomodoro",
                    "Chúc mừng! Đã hoàn thành một phiên học.",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            try:
                subprocess.Popen(
                    "notify-send -i accessories-calculator 'Pomodoro' 'Chúc mừng! Đã hoàn thành một phiên học.' &",
                    shell=True,
                )
            except Exception:
                pass

    def on_session_finished(self) -> None:
        """Xử lý khi một phiên đếm ngược thực tế chạy đủ thời gian về 00:00."""
        self.pomo_running = False
        if self.pomo_timer:
            self.pomo_timer.pause()

        if self.pomo_mode == "work":
            # Chỉ ghi nhận phiên khi đếm ngược thực tế đủ 25 phút về 00:00
            self.completed_pomodoros += 1
            self.total_focus_minutes += 25

            # Phát chuông hệ thống & bắn thông báo desktop nổi
            self.play_session_alerts()

            # Lấy tên môn học từ Input
            subject_input = self.query_one("#subject-input", Input)
            subject_name = subject_input.value.strip() or "Học tập tự do"

            timestamp_str = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
            stt_str = str(self.completed_pomodoros)
            duration_str = "25 phút"
            status_str = "✅ Hoàn thành"

            # 1. Ghi vĩnh viễn vào tệp CSV
            self.append_session_to_csv(stt_str, timestamp_str, subject_name, duration_str, status_str)

            # 2. Hiển thị lên bảng DataTable
            table = self.query_one("#log-table", DataTable)
            table.add_row(stt_str, timestamp_str, subject_name, duration_str, status_str)
            table.scroll_end(animate=False)

            self.notify(
                f"Đã ghi nhận vào CSV: {subject_name}",
                title="🎉 Hoàn thành phiên Pomodoro 25 phút!",
                severity="information",
                timeout=8,
            )

            # Chuyển sang chế độ nghỉ giải lao 5 phút (tự động bỏ chặn web)
            self.switch_to_mode("break")
        else:
            self.bell()
            # Hết 5 phút nghỉ giải lao
            self.notify(
                "Đã hết 5 phút giải lao! Hãy bắt đầu phiên tập trung tiếp theo.",
                title="☕ Hết giờ nghỉ ngơi",
                severity="information",
                timeout=8,
            )
            # Chuyển lại về chế độ học tập 25 phút
            self.switch_to_mode("work")

    def switch_to_mode(self, mode: str) -> None:
        """Chuyển đổi giữa chế độ Học (Work) và Nghỉ (Break)."""
        self.pomo_mode = mode
        self.pomo_running = False
        if self.pomo_timer:
            self.pomo_timer.pause()

        timer_card = self.query_one("#timer-card")
        badge = self.query_one("#timer-badge", Label)
        mode_btn = self.query_one("#btn-toggle-mode", Button)

        if mode == "work":
            self.pomo_seconds_left = self.WORK_DURATION
            badge.update("🎯 ĐANG TRONG PHIÊN HỌC TẬP (25 PHÚT)")
            badge.remove_class("mode-break-badge")
            timer_card.remove_class("mode-break-card")
            mode_btn.label = "☕ Chuyển sang Nghỉ"
        else:
            # Chế độ Nghỉ giải lao: Bỏ chặn web xao nhãng để người dùng thư giãn
            self.deactivate_web_blocker()
            self.pomo_seconds_left = self.BREAK_DURATION
            badge.update("☕ ĐANG TRONG PHIÊN NGHỈ GIẢI LAO (5 PHÚT)")
            badge.add_class("mode-break-badge")
            timer_card.add_class("mode-break-card")
            mode_btn.label = "🎯 Chuyển sang Học"

        self.update_timer_display()
        self.update_stats_panel()

    # --- Xử lý sự kiện nút bấm & Input ---

    @on(Input.Submitted, "#subject-input")
    def on_subject_submitted(self, event: Input.Submitted) -> None:
        """Xử lý khi người dùng nhấn Enter trong ô nhập liệu môn học."""
        subject = event.value.strip() or "Học tập tự do"
        self.notify(f"Đã lưu mục tiêu: {subject}", title="🎯 Mục tiêu phiên học", timeout=3)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-start":
            self.start_timer()
        elif button_id == "btn-pause":
            self.pause_timer()
        elif button_id == "btn-reset":
            self.reset_timer()
        elif button_id == "btn-toggle-mode":
            self.toggle_mode()
        elif button_id == "btn-delete-log":
            self.delete_selected_log()

    def start_timer(self) -> None:
        """Bắt đầu chạy đồng hồ Pomodoro. Nếu là phiên học 25p, tự động kích hoạt chặn web."""
        if not self.pomo_running:
            self.pomo_running = True
            if self.pomo_timer:
                self.pomo_timer.resume()

            if self.pomo_mode == "work":
                # Kích hoạt chặn web xao nhãng trong phiên học tập
                self.activate_web_blocker()
                self.notify("Đã bắt đầu phiên học tập! Hãy tập trung cao độ.", severity="information", timeout=3)
            else:
                self.notify("Đã bắt đầu phiên nghỉ ngơi giải lao!", severity="information", timeout=3)

            self.update_stats_panel()

    def pause_timer(self) -> None:
        """Tạm dừng đồng hồ Pomodoro."""
        if self.pomo_running:
            self.pomo_running = False
            if self.pomo_timer:
                self.pomo_timer.pause()
            self.update_stats_panel()
            self.notify("Đã tạm dừng đồng hồ.", severity="warning", timeout=3)

    def reset_timer(self) -> None:
        """Đặt lại đồng hồ về ban đầu và tự động bỏ chặn web (khôi phục mạng)."""
        self.pomo_running = False
        if self.pomo_timer:
            self.pomo_timer.pause()

        # Khi bấm Đặt lại: Khôi phục lại mạng bình thường
        self.deactivate_web_blocker()

        self.pomo_seconds_left = (
            self.WORK_DURATION if self.pomo_mode == "work" else self.BREAK_DURATION
        )
        self.update_timer_display()
        self.update_stats_panel()
        self.notify("Đã đặt lại đồng hồ & khôi phục mạng bình thường.", severity="information", timeout=3)

    def toggle_mode(self) -> None:
        """Đổi qua lại giữa chế độ Học tập và Nghỉ giải lao."""
        next_mode = "break" if self.pomo_mode == "work" else "work"
        self.switch_to_mode(next_mode)
        mode_label = "Nghỉ ngơi (5 phút)" if next_mode == "break" else "Học tập (25 phút)"
        self.notify(f"Chuyển sang chế độ: {mode_label}", timeout=3)

    # --- Phím tắt (Action Handlers) ---

    def action_toggle_timer(self) -> None:
        """Phím Space: Bắt đầu hoặc tạm dừng."""
        if self.pomo_running:
            self.pause_timer()
        else:
            self.start_timer()

    def action_reset_timer(self) -> None:
        """Phím R: Đặt lại đồng hồ và khôi phục mạng."""
        self.reset_timer()

    def action_toggle_mode(self) -> None:
        """Phím M: Đổi chế độ Học/Nghỉ."""
        self.toggle_mode()

    def action_test_complete(self) -> None:
        """Phím T: Thử nghiệm phát chuông và chuyển sang Nghỉ giải lao (KHÔNG ghi vào CSV hay tăng thống kê)."""
        self.pomo_running = False
        if self.pomo_timer:
            self.pomo_timer.pause()

        # 1. Vẫn phát chuông âm thanh paplay và bắn thông báo desktop
        self.play_session_alerts()

        # 2. Chuyển sang chế độ nghỉ giải lao 5 phút (và tự động bỏ chặn web)
        self.switch_to_mode("break")

        # 3. Thông báo rõ ràng cho người dùng
        self.notify(
            "Đã phát chuông & chuyển sang Nghỉ giải lao (Test).\nPhiên test KHÔNG được ghi vào lịch sử học tập.",
            title="🧪 Thử nghiệm (Không lưu dữ liệu)",
            severity="information",
            timeout=6,
        )

    def action_delete_selected_log(self) -> None:
        """Phím D hoặc Delete: Xóa dòng nhật ký đang chọn khỏi bảng và CSV."""
        self.delete_selected_log()

    def action_quit_app(self) -> None:
        """Phím Q: Gỡ bỏ chặn web và thoát ứng dụng an toàn."""
        self.deactivate_web_blocker()
        self.exit()


if __name__ == "__main__":
    app = StudyDashboardApp()
    app.run()
