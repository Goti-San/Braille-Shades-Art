#!/usr/bin/env python3

# ==========================================
# DEPENDENCIES & LIBRARIES
# ==========================================
# Standard libraries, no installation required):
#   os, sys, tty, termios, random, re, contextlib
# External, included locally in the script folder):
#   - Python3-pil / Pillow (image import and export)
#   - Python3-pyperclip (clipboard functionality)
#   - Xclip (Linux binary executable for clipboard)
#   - FreeMono.ttf (text font for image rendering)

import os
import sys
import tty
import termios
import random
import re
from contextlib import contextmanager

# Path configuration to bypass Python and Linux default directories
# This forces the script to read local libraries and binaries
# directly from this .py file's current folder
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
os.environ["PATH"] += os.pathsep + script_dir

WORKSPACE_FILE = "Braille_Shades_Art_workspace.txt"

WIDTH = 72
HALF_WIDTH = 36

braille_history = []

# ==========================================
# FILE I/O UTILS (Core engine)
# ==========================================


def read_workspace_content():
    if not os.path.exists(WORKSPACE_FILE):
        return None
    with open(WORKSPACE_FILE, "r", encoding="utf-8") as f:
        return f.read()


def write_workspace_content(content):
    with open(WORKSPACE_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def read_workspace_lines(strip_newlines=True):
    if not os.path.exists(WORKSPACE_FILE):
        return None
    with open(WORKSPACE_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        cleaned_lines = []
        for line in lines:
            line_clean = remove_hidden_unicode(line)
            if strip_newlines:
                cleaned_lines.append(line_clean.rstrip("\r\n"))
            else:
                cleaned_lines.append(line_clean)
        return cleaned_lines


def remove_hidden_unicode(text):
    return re.sub(r"[\u200B\u200C\u200D\uFEFF]", "", text)


def write_workspace_lines(lines, append_newline=True):
    with open(WORKSPACE_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            clean_line = line.rstrip("\r\n")
            f.write(clean_line + "\n")


# ==========================================
# TERMINAL UI UTILS
# ==========================================


def clear_screen():
    sys.stdout.write("\033[H\033[2J\033[3J")
    sys.stdout.flush()


@contextmanager
def safe_terminal():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        try:
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except Exception:
            pass


def wait_for_key():
    with safe_terminal():
        return sys.stdin.read(1)


def input_with_esc(prompt):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    chars = []

    with safe_terminal():
        while True:
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                sys.stdout.write("\r\n")
                return None
            elif ch in ("\r", "\n"):
                sys.stdout.write("\r\n")
                return "".join(chars)
            elif ch in ("\x7f", "\x08"):
                if chars:
                    chars.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif ch.isprintable():
                chars.append(ch)
                sys.stdout.write(ch)
                sys.stdout.flush()


def input_number(prompt):
    val = input_with_esc(prompt)
    if val is None:
        return None
    val = val.strip().lower()
    if val == "n" or val == "":
        return None
    try:
        return int(val)
    except ValueError:
        return None


def prompt_yn(prompt, default=False):
    while True:
        val = input_with_esc(prompt)
        if val is None:
            return None
        val = val.strip().lower()
        if val == "y":
            return True
        elif val == "n":
            return False
        elif val == "":
            return default


# ==========================================
# IMPORT / EXPORT IMAGE ENGINE
# ==========================================


def prompt_color(prompt_str, default_color, default_alpha_pct=None):
    try:
        from PIL import ImageColor
    except ImportError:
        return False

    c_input = input_with_esc(prompt_str)
    if c_input is None:
        return None
    c_str = c_input.strip() or default_color

    try:
        rgb = ImageColor.getrgb(c_str)
        r, g, b = rgb[:3]
    except ValueError as e:
        print(f"\n[!] ERROR in color format: {e}")
        return False

    if default_alpha_pct is not None:
        alpha_in = input_with_esc(" Add transparency % to this color? [Y/n] (Default: n): ")
        if alpha_in is None:
            return None
        a_val = alpha_in.strip()
        if not a_val:
            alpha = int(((100 - default_alpha_pct) / 100.0) * 255)
        else:
            try:
                pct = int(a_val)
                pct = max(0, min(100, pct))
                alpha = int(((100 - pct) / 100.0) * 255)
            except ValueError:
                alpha = int(((100 - default_alpha_pct) / 100.0) * 255)
    else:
        wants_alpha_str = input_with_esc(" Add transparency % to this color? [Y/n] (Default: n): ")
        if wants_alpha_str is None:
            return None
        wants_alpha = wants_alpha_str.strip().lower() == "y"
        if wants_alpha:
            alpha_in = input_number(" Transparency % (0-100): ")
            if alpha_in is None:
                return None
            pct = max(0, min(100, alpha_in))
            alpha = int(((100 - pct) / 100.0) * 255)
        else:
            alpha = 255

    return (r, g, b, alpha)


def handle_image_menu():
    made_changes = False
    while True:
        clear_screen()
        print("=" * WIDTH)
        print("[Import or export image]".center(WIDTH))
        print("=" * WIDTH)
        print("- D to Import image to workspace with Braille Dots")
        print("- S to Import image to workspace with Block Shades")
        print("\n- E to Export workspace to image .png")
        print("\n Use these commands to correct the spacing:")
        print("[noparse]Steam comments section[/noparse]")
        print("/code Steam chats")
        print("```Discord/WhastsApp```")
        print("`Discord`")
        print("\nPress ESC to go back...")

        key = wait_for_key()

        if key == "\x1b":
            return made_changes
        elif key.lower() == "d":
            if import_image_to_workspace():
                made_changes = True
        elif key.lower() == "s":
            if import_image_to_workspace_block_shades():
                made_changes = True
        elif key.lower() == "e":
            export_workspace_to_image()


def export_workspace_to_image():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("\n[!] ERROR: The 'Pillow' (Python3-pil) library is required to use this function")
        print("\nPress any key to go back...")
        wait_for_key()
        return False

    lines = read_workspace_lines(strip_newlines=True)
    if not lines:
        print("\n[!] ERROR: Workspace is empty")
        print("\nPress any key to go back...")
        wait_for_key()
        return False

    while lines and not lines[-1].strip(" \t\u2800\u00a0"):
        lines.pop()

    if not lines:
        print("\n[!] ERROR: Workspace only contains invisible characters")
        print("\nPress any key to go back...")
        wait_for_key()
        return False

    cleaned_lines = []
    max_cols = 0
    for line in lines:
        stripped = line.rstrip(" \t\u2800\u00a0")
        visible_len = len(re.sub(r"[\u200B\u200C\u200D]", "", stripped))
        if visible_len > max_cols:
            max_cols = visible_len
        cleaned_lines.append(stripped)
    lines = cleaned_lines

    clear_screen()
    print("=" * WIDTH)
    print("[Export workspace to image]".center(WIDTH))
    print("=" * WIDTH)
    print(" Press Enter leaving blank to use default values")
    print(" Use standard color names (e.g. black, red)")
    print(" Hex code are valid (e.g. #2C2F33 is Discord Dark background)")
    print("=" * WIDTH)

    h_spacing_val = input_with_esc(" Horizontal spacing between characters (default: 0.83) [0.1-2]: ")
    if h_spacing_val is None:
        return False
    h_spacing_str = h_spacing_val.strip()

    if not h_spacing_str:
        h_spacing = 0.83
    else:
        try:
            h_spacing = float(h_spacing_str)
            h_spacing = max(0.1, min(2.0, h_spacing))
        except ValueError:
            h_spacing = 0.83

    v_spacing_val = input_with_esc(" Vertical space between characters (default: 1) [0.1-2]: ")
    if v_spacing_val is None:
        return False
    v_spacing_str = v_spacing_val.strip()

    if not v_spacing_str:
        v_spacing = 1.0
    else:
        try:
            v_spacing = float(v_spacing_str)
            v_spacing = max(0.1, min(2.0, v_spacing))
        except ValueError:
            v_spacing = 1.0

    bg_rgba = prompt_color(" Background color (Default: #121212 Material Dark): ", "#121212")
    if bg_rgba is None or bg_rgba is False:
        if bg_rgba is False:
            wait_for_key()
        return False

    dot_rgba = prompt_color(" Braille/Shades color (Default: darkgray): ", "darkgray")
    if dot_rgba is None or dot_rgba is False:
        if dot_rgba is False:
            wait_for_key()
        return False

    draw_grid = prompt_yn(" Draw cell grid? [Y/n] (Default: y) : ", default=True)
    if draw_grid is None:
        return False

    if draw_grid:
        grid_rgba = prompt_color(" Cell grid color (Default: #1A1A1A Chinese Black): ", "#1A1A1A")

        if grid_rgba is None or grid_rgba is False:
            if grid_rgba is False:
                wait_for_key()
            return False
    else:
        grid_rgba = (0, 0, 0, 0)

    draw_border = prompt_yn(" Add a border to the image? [Y/n] (Default: y): ", default=True)
    if draw_border is None:
        return False

    border_lines = 0
    if draw_border:
        b_lines = input_number(" How many lines? (Default: 1): ")
        border_lines = 1 if b_lines is None else max(1, b_lines)

        border_rgba = prompt_color(" Border color (Default: #1A1A1A Chinese Black): ", "#1A1A1A")
        if border_rgba is None or border_rgba is False:
            if border_rgba is False:
                wait_for_key()
            return False
    else:
        border_rgba = (0, 0, 0, 0)

    title_input = input_with_esc(" Enter an optional title for the image (Default: none): ")
    if title_input is None:
        return False
    title_text = title_input.strip()

    title_rgba = dot_rgba
    if title_text:
        default_title_hex = f"#{dot_rgba[0]:02x}{dot_rgba[1]:02x}{dot_rgba[2]:02x}"
        default_alpha_pct = int(100 - (dot_rgba[3] / 255.0 * 100))
        title_rgba = prompt_color(" Title color (Default: same as Braille dots): ", default_title_hex, default_alpha_pct)
        if title_rgba is None or title_rgba is False:
            if title_rgba is False:
                wait_for_key()
            return False

    scale_val = input_with_esc(" Enter PNG size [0.1-10] 1 is original size (Default: 0.50): ")
    if scale_val is None:
        return False
    scale_str = scale_val.strip()

    if not scale_str:
        scale = 0.50
    else:
        try:
            scale = float(scale_str)
            scale = max(0.1, min(10.0, scale))
        except ValueError:
            scale = 1.0

    print("\n Loading...")

    font_path = os.path.join(script_dir, "FreeMono.ttf")

    if not os.path.exists(font_path):
        print("\n[!] ERROR: The file 'FreeMono.ttf' is not found in the program folder (.py)")
        print(" Canceling export...")
        print("\nPress any key to go back...")
        wait_for_key()
        return False

    font_size = int(32 * scale)
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        print(f"\n[!] Error loading font: {e}")
        wait_for_key()
        return False

    num_lines = len(lines)

    left, top, right, bottom = font.getbbox("⣿")
    char_width = font.getlength("⣿") * h_spacing
    char_height = (bottom - top + int(font_size * 0.2)) * v_spacing

    title_height = 0
    if title_text:
        _, t_top, _, t_bottom = font.getbbox(title_text)
        title_height = t_bottom - t_top + int(font_size * 0.4)

    img_width = int(max_cols * char_width)
    if title_text:
        t_width = font.getlength(title_text)
        if t_width > img_width:
            img_width = int(t_width)

    img_height = int((num_lines * char_height) + title_height)

    if border_lines > 0:
        border_x = int(border_lines * char_width)
        border_y = int(border_lines * char_height)
        top_border_y = border_y
    else:
        border_x = 0
        border_y = 0
        top_border_y = 0

    tot_width = img_width + (border_x * 2)
    tot_height = img_height + top_border_y + border_y

    if tot_width <= 0:
        tot_width = 1
    if tot_height <= 0:
        tot_height = 1

    img = Image.new("RGBA", (tot_width, tot_height), bg_rgba)
    draw = ImageDraw.Draw(img, "RGBA")

    if border_lines > 0:
        if top_border_y > 0:
            draw.rectangle([0, 0, tot_width, top_border_y], fill=border_rgba)
        if border_y > 0:
            draw.rectangle([0, tot_height - border_y, tot_width, tot_height], fill=border_rgba)
        if border_x > 0:
            draw.rectangle([0, 0, border_x, tot_height], fill=border_rgba)
        if border_x > 0:
            draw.rectangle([tot_width - border_x, 0, tot_width, tot_height], fill=border_rgba)

    offset_x = border_x
    offset_y = top_border_y

    if title_text:
        t_width = font.getlength(title_text)
        t_x = offset_x + (img_width - t_width) / 2
        draw.text((t_x, offset_y), title_text, font=font, fill=title_rgba)

    if draw_grid:
        try:
            grid_width = max(1, int(scale))
            for col in range(max_cols + 1):
                x = offset_x + int(col * char_width)
                draw.line([(x, offset_y + title_height), (x, offset_y + img_height)], fill=grid_rgba, width=grid_width)

            for row in range(num_lines + 1):
                y = offset_y + int(title_height + (row * char_height))
                draw.line([(offset_x, y), (offset_x + int(max_cols * char_width), y)], fill=grid_rgba, width=grid_width)
        except Exception:
            pass

    y_text = offset_y + title_height
    for line in lines:
        x_text = offset_x
        for ch in line:
            cx = x_text + (char_width / 2)
            cy = y_text + (char_height / 2)
            draw.text((cx, cy), ch, font=font, fill=dot_rgba, anchor="mm")
            x_text += char_width
        y_text += char_height

    out_name = "Braille_Shades_Art_export.png"

    try:
        img.save(out_name)
        print(f"\n[!] SUCCESS: Image exported as '{out_name}'")
        print(f" Dimensions: {tot_width}x{tot_height} pixels")
    except Exception as e:
        print(f"\n[!] ERROR saving image: {e}")

    print("\nPress any key to continue...")
    wait_for_key()
    return True


def import_image_to_workspace():
    try:
        from PIL import Image
    except ImportError:
        print("\n[!] ERROR: The 'Pillow' (Python3-pil) library is required to use this function")
        print("\nPress any key to go back...")
        wait_for_key()
        return False

    clear_screen()
    print("=" * WIDTH)
    print("[Import image to workspace with ASCII Braille dots]".center(WIDTH))
    print("=" * WIDTH)
    print("[!] CAUTION: Overwrite 'Braille_Shades_Art_workspace.txt")
    print(" Image must have been modified to 1-Bit Bold Line Art (e.g using GIMP program)")
    print(" The image can only have the colors: '⣿' black, '⠀' white")
    print(" Enter the image path or name (e.g. drawing.png)")
    print(" Uppercase-lowercase does not affect")
    print(" Leave blank and press Enter or press Esc to go back...")

    while True:
        img_path = input_with_esc("> ")
        if img_path is None or not img_path.strip():
            return False
        img_path = img_path.strip()

        if not os.path.exists(img_path):
            dir_name = os.path.dirname(img_path) or "."
            base_name = os.path.basename(img_path).lower()
            found = False
            if os.path.exists(dir_name):
                for f in os.listdir(dir_name):
                    if f.lower() == base_name:
                        img_path = os.path.join(dir_name, f)
                        found = True
                        break
            if not found:
                print(f"\n[!] ERROR: Image file '{img_path}' not found, try again\n")
                continue
        break

    max_cols = input_number(" Max columns for the final design (e.g. 43 for Steam): ")
    if max_cols is None or max_cols <= 0:
        return False

    print(" Set darkness detection threshold from 1 to 255")
    threshold = input_number(" Leave blank and press Enter to 255: ")
    if threshold is None or not (1 <= threshold <= 255):
        threshold = 128

    try:
        img = Image.open(img_path)
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            alpha = img.convert("RGBA").split()[-1]
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=alpha)
            img = bg.convert("L")
        else:
            img = img.convert("L")
    except Exception as e:
        print(f"\n[!] ERROR opening image: {e}")
        print("\nPress any key to go back...")
        wait_for_key()
        return False

    target_width = max_cols * 2
    target_height = int((img.height * target_width) / img.width)

    target_height = ((target_height + 3) // 4) * 4
    if target_height == 0:
        target_height = 4

    img = img.resize((target_width, target_height), Image.Resampling.NEAREST)

    dot_map = [[(0, 0), 0x01], [(0, 1), 0x02], [(0, 2), 0x04], [(0, 3), 0x40], [(1, 0), 0x08], [(1, 1), 0x10], [(1, 2), 0x20], [(1, 3), 0x80]]

    new_lines = []

    for y in range(0, target_height, 4):
        line_chars = []
        for x in range(0, target_width, 2):
            offset = 0
            for (dx, dy), bit in dot_map:
                px = x + dx
                py = y + dy
                if px < target_width and py < target_height:
                    if img.getpixel((px, py)) < threshold:
                        offset |= bit

            line_chars.append(chr(0x2800 + offset))
        new_lines.append("".join(line_chars))

    write_workspace_lines(new_lines)
    print(f"\n[!] SUCCESS: The result has been saved to '{WORKSPACE_FILE}'")
    print(f" Generated dimensions: {max_cols} columns x {len(new_lines)} lines.")
    print("\nPress any key to continue...")
    wait_for_key()
    return True


def import_image_to_workspace_block_shades():
    try:
        from PIL import Image
    except ImportError:
        print("\n[!] ERROR: The 'Pillow' (Python3-pil) library is required to use this function")
        print("\nPress any key to go back...")
        wait_for_key()
        return False

    clear_screen()
    print("=" * WIDTH)
    print("[Import image to workspace with Block Shades]".center(WIDTH))
    print("=" * WIDTH)
    print("[!] CAUTION: Overwrite 'Braille_Shades_Art_workspace.txt")
    print(" Image must have been modified to 2-Bit Bold Line Art (e.g using GIMP program)")
    print(" The image can only have the colors:")
    print(" '██' black, '▓▓' dark gray, '▒▒' light gray, '░░' white")
    print(" Enter the image path or name (e.g. drawing.png)")
    print(" Uppercase-lowercase does not affect")
    print(" Leave blank and press Enter or press Esc to go back...")

    while True:
        img_path = input_with_esc("> ")
        if img_path is None or not img_path.strip():
            return False
        img_path = img_path.strip()

        if not os.path.exists(img_path):
            dir_name = os.path.dirname(img_path) or "."
            base_name = os.path.basename(img_path).lower()
            found = False
            if os.path.exists(dir_name):
                for f in os.listdir(dir_name):
                    if f.lower() == base_name:
                        img_path = os.path.join(dir_name, f)
                        found = True
                        break
            if not found:
                print(f"\n[!] ERROR: Image file '{img_path}' not found, try again\n")
                continue
        break

    max_cols = input_number(" Max columns for the final design (e.g. 43 for Steam): ")
    if max_cols is None or max_cols <= 0:
        return False

    block_width = input_number(" Import with 1 or 2 Block Shades [1-2] (Default: 2): ")
    if block_width is None:
        block_width = 2
    elif block_width not in (1, 2):
        return False

    block_black = "█" * block_width
    block_dark = "▓" * block_width
    block_light = "▒" * block_width
    block_white = "░" * block_width

    try:
        img = Image.open(img_path)
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            alpha = img.convert("RGBA").split()[-1]
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=alpha)
            img = bg.convert("L")
        else:
            img = img.convert("L")
    except Exception as e:
        print(f"\n[!] ERROR opening image: {e}")
        print("\nPress any key to go back...")
        wait_for_key()
        return False

    target_width = max_cols
    target_height = int((img.height * target_width) / img.width)

    if target_height == 0:
        target_height = 1

    img = img.resize((target_width, target_height), Image.Resampling.NEAREST)

    new_lines = []

    for y in range(target_height):
        line_chars = []
        for x in range(target_width):
            pixel_val = img.getpixel((x, y))

            if pixel_val < 64:
                line_chars.append(block_black)
            elif pixel_val < 128:
                line_chars.append(block_dark)
            elif pixel_val < 192:
                line_chars.append(block_light)
            else:
                line_chars.append(block_white)

        new_lines.append("".join(line_chars))

    write_workspace_lines(new_lines)
    print(f"\n[!] SUCCESS: The result has been saved to '{WORKSPACE_FILE}'")
    print(f" Generated dimensions: {max_cols} columns x {len(new_lines)} lines.")
    print("\nPress any key to continue...")
    wait_for_key()
    return True


# ==========================================
# CORE ANALYSIS & INFO
# ==========================================


def analyze_Braille_Shades_Art_workspace():
    raw_content = read_workspace_content()
    if raw_content is None:
        print(f"[!] ERROR: File '{WORKSPACE_FILE}' not found\n[!] Press N to create a new file")
        return None, None

    if not raw_content:
        return None, None

    lines_list = raw_content.splitlines() if raw_content.endswith("\n") else raw_content.split("\n")
    text_to_measure = "\n".join(lines_list) if raw_content.endswith("\n") else raw_content

    total_bytes = len(text_to_measure.encode("utf-8"))
    num_lines = len(lines_list)
    num_characters = len(text_to_measure)
    num_columns = max(len(line) for line in lines_list) if lines_list else 0
    right_dots_only = 0
    for char in text_to_measure:
        if "\u2801" <= char <= "\u28ff":
            if (ord(char) - 0x2800) & 71 == 0:
                right_dots_only += 1

    print(f"Cols: {num_columns} | Lns: {num_lines} | Chars: {num_characters} | Size: {total_bytes} bytes | R-dots only: {right_dots_only}".center(WIDTH))
    print("=" * WIDTH)

    return True, raw_content


def show_platform_information():
    raw_content = read_workspace_content()
    total_bytes = num_columns = right_dots_only = num_lines = num_characters = 0

    if raw_content:
        lines_list = raw_content.splitlines() if raw_content.endswith("\n") else raw_content.split("\n")
        text_to_measure = "\n".join(lines_list) if raw_content.endswith("\n") else raw_content

        total_bytes = len(text_to_measure.encode("utf-8"))
        num_columns = max(len(line) for line in lines_list) if lines_list else 0
        num_lines = len(lines_list)
        num_characters = len(text_to_measure)

        for char in raw_content:
            if "\u2801" <= char <= "\u28ff":
                if (ord(char) - 0x2800) & 71 == 0:
                    right_dots_only += 1

    def get_status(is_ok):
        return "Status: [OK]" if is_ok else "Status: [BAD]"

    # --- Steam config ---
    steam_ok = (num_columns <= 43) and (total_bytes <= 999)
    steam_l1 = "[Steam comments section]"
    steam_l2 = f"Cols: {num_columns}/43"
    steam_l3 = f"{total_bytes}/999 bytes"
    steam_l4 = get_status(steam_ok)

    # --- YouTube config ---
    yt_ok = num_columns <= 32
    yt_l1 = "[YouTube comments]"
    yt_l2 = f"Cols: {num_columns}/32"
    yt_l3 = ""
    yt_l4 = get_status(yt_ok)

    # --- Discord mobile config ---
    disc_ok = num_columns <= 34
    disc_l1 = "[Discord mobile]"
    disc_l2 = f"Cols: {num_columns}/34"
    disc_l3 = ""
    disc_l4 = get_status(disc_ok)

    # --- Discord profile config ---
    discpro_ok = (num_columns <= 34) and (num_lines <= 3) and (num_characters <= 190)
    discpro_l1 = "[Discord profile] Not allow spaces"
    discpro_l2 = f"Cols: {num_columns}/26 Lns: {num_lines}/3"
    discpro_l3 = f"Chars: {num_characters}/190"
    discpro_l4 = get_status(discpro_ok)

    # --- Instagram & WhatsApp config ---
    ig_ok = num_columns <= 23
    ig_l1 = "[Instagram & WhatsApp]"
    ig_l2 = f"Cols: {num_columns}/23"
    ig_l3 = ""
    ig_l4 = get_status(ig_ok)

    def pad(text):
        return f" {text}"[:HALF_WIDTH].ljust(HALF_WIDTH)

    clear_screen()
    print("=" * WIDTH)
    print("[Information platform compatibility status]".center(WIDTH))
    print("=" * WIDTH)

    print(pad(steam_l1) + "│" + pad(yt_l1))
    print(pad(steam_l2) + "│" + pad(yt_l2))
    print(pad(steam_l3) + "│" + pad(yt_l3))
    print(pad(steam_l4) + "│" + pad(yt_l4))

    print("─" * HALF_WIDTH + "┼" + "─" * HALF_WIDTH)

    print(pad(disc_l1) + "│" + pad(discpro_l1))
    print(pad(disc_l2) + "│" + pad(discpro_l2))
    print(pad(disc_l3) + "│" + pad(discpro_l3))
    print(pad(disc_l4) + "│" + pad(discpro_l4))

    print("─" * HALF_WIDTH + "┼" + "─" * HALF_WIDTH)

    print(pad(ig_l1) + "│" + "Mobile App's right-dots only".center(HALF_WIDTH))
    print(pad(ig_l2) + "│" + "will swap to the left-dots".center(HALF_WIDTH))
    print(pad(ig_l3) + "│" + pad(""))
    print(pad(ig_l4) + "│" + f"Right-dots only: {right_dots_only}".center(HALF_WIDTH))

    print("=" * WIDTH)

    print("\n- E to Export information in 'Braille_Shades_Art_info.txt'")
    print("- V to View top 10 heaviest lines")
    print("\nPress ESC or any other key to go back...")
    key = wait_for_key()

    if key.lower() == "e":
        print()
        if prompt_yn("Do you want to create or overwrite 'Braille_Shades_Art_info.txt'? [Y/n]: "):
            export_content = f"==============================\n [Information platform compatibility status]\n Mobile App's right-dots only will swap to the left-dots\n Right-dots only: {right_dots_only}\n==============================\n {steam_l1}\n {steam_l2}\n {steam_l3}\n {steam_l4}\n==============================\n {yt_l1}\n {yt_l2}\n\n {yt_l4}\n==============================\n {disc_l1}\n {disc_l2}\n\n {disc_l4}\n==============================\n {discpro_l1}\n {discpro_l2}\n {discpro_l3}\n {discpro_l4}\n==============================\n {ig_l1}\n {ig_l2}\n\n {ig_l4}\n==============================\n"
            with open("Braille_Shades_Art_info.txt", "w", encoding="utf-8") as f:
                f.write(export_content)
    elif key.lower() == "v":
        show_heaviest_lines()


def show_heaviest_lines():
    lines = read_workspace_lines(strip_newlines=False)

    clear_screen()
    print("=" * WIDTH)
    print("[View top 10 heaviest lines]".center(WIDTH))
    print("=" * WIDTH)

    if not lines:
        print(" No lines found in the workspace")
    else:
        line_weights = [(i + 1, len(line.encode("utf-8")) + (1 if i < len(lines) - 1 else 0)) for i, line in enumerate(lines)]
        heavy_lines = sorted(line_weights, key=lambda x: x[1], reverse=True)

        for rank, (num, size) in enumerate(heavy_lines[:10], 1):
            print(f" {rank}. Line {num}: {size} bytes")

    print("\nPress any key to go back...")
    wait_for_key()


# ==========================================
# TEXT GENERATOR WITH AESTHETIC TYPOGRAPHY
# ==========================================


def text_generator(text):
    NORMAL_62 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    NORMAL_52 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

    FONTS_62 = [
        ("Monospace", "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"),
        ("Sans-Serif", "𝖺𝖻𝖼𝖽𝖾𝖿𝗀𝗁𝗂𝗃𝗄𝗅𝗆𝗇𝗈𝗉𝗊𝗋𝗌𝗍𝗎𝗏𝗐𝗑𝗒𝗓𝖠𝖡𝖢𝖣𝖤𝖥𝖦𝖧𝖨𝖩𝖪𝖫𝖬𝖭𝖮𝖯𝖰𝖱𝖲𝖳𝖴𝖵𝖶𝖷𝖸𝖹𝟢𝟣𝟤𝟥𝟦𝟧𝟨𝟩𝟪𝟫"),
        ("Sans-Serif Bold", "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"),
        ("Serif Bold", "𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"),
        ("Cyberpunk / Terminal", "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"),
        ("Double Struck / Blackboard", "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡"),
        ("Squared", "🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉0123456789"),
        ("Circled", "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ⓪①②③④⑤⑥⑦⑧⑨"),
        ("Squared Negative", "🅰🅱🅲🅳🅴🅵🅶🅷🅸🅹🅺🅻🅼🅽🅾🅿🆀🆁🆂🆃🆄🅅🆆🅇🆈🆉🅰🅱🅲🅳🅴🅵🅶🅷🅸🅹🅺🅻🅼🅽🅾🅿🆀🆁🆂🆃🆄🅅🆆🅇🆈🆉0123456789"),
        ("Circled Negative", "🅐🅑🅒🅓🅔🅕🅖🅗🅘🅙🅚🅛🅜🅝🅞🅟🅠🅡🅢🅣🅤🅥🅦🅧🅨🅩🅐🅑🅒🅓🅔🅕🅖🅗🅘🅙🅚🅛🅜🅝🅞🅟🅠🅡🅢🅣🅤🅥🅦🅧🅨🅩⓿❶❷❸❹❺❻❼❽❾"),
        ("Leetspeak", "4bcd3f9h1jklmn0pqrs7uvwxyz48CD3F6H1JKLMN0PQR57UVWXYZ0123456789"),
        ("Superscript", "ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖᵠʳˢᵗᵘᵛʷˣʸᶻᴬᴮᶜᴰᴱᶠᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾQᴿˢᵀᵁⱽᵂˣʸᶻ⁰¹²³⁴⁵⁶⁷⁸⁹"),
        ("Ancient / Runes", "ᛅᛒᚢᛑᛂᚠᚵᚻᛁᛃᚴᛚᛘᚿᚮᛔᛩᚱᛋᛏᚢᚡᚥᛪᛦᛨᛆᛒᚢᛑᛂᚠᚵᚻᛁᛃᚴᛚᛘᚿᚮᛔᛩᚱᛋᛏᚢᚡᚥᛪᛦᛨ0123456789"),
        ("Fullwidth / Vaporwave", "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ０１２３４５６７８９"),
    ]

    FONTS_52 = [
        ("Sans-Serif Italic", "𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡"),
        ("Sans-Serif Bold Italic", "𝙖𝙗𝙘𝙙𝙚𝙛𝙜𝙝𝙞𝙟𝙠𝙡𝙢𝙣𝙤𝙥𝙦𝙧𝙨𝙩𝙪𝙫𝙬𝙭𝙮𝙯𝘼𝘽𝘾𝘿𝙀𝙁𝙂𝙃𝙄𝙅𝙆𝙇𝙈𝙉𝙊𝙋𝙌𝙍𝙎𝙏𝙐𝙑𝙒𝙓𝙔𝙕"),
        ("Fraktur / Gothic", "𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ"),
        ("Fraktur Bold", "𝖆𝖇𝖈𝖉𝖊𝖋𝖌𝖍𝖎𝖏𝖐𝖑𝖒𝖓𝖔𝖕𝖖𝖗𝖘𝖙𝖚𝖛𝖜𝖝𝖞𝖟𝕬𝕭𝕮𝕯𝕰𝕱𝕲𝕳𝕴𝕵𝕶𝕷𝕸𝕹𝕺𝕻𝕼𝕽𝕾𝕿𝖀𝖁𝖂𝖃𝖄𝖅"),
        ("Script Normal", "𝒶𝒷𝒸𝒹ℯ𝒻ℊ𝒽𝒾𝒿𝓀𝓁𝓂𝓃ℴ𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝒵𝒜ℬ𝒞𝒟ℰℱ𝒢ℋℐ𝒥𝒦ℒℳ𝒩𝒪𝒫𝒬ℛ𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵"),
        ("Script Cursive", "𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩"),
        ("Math Italic", "𝑎𝑏𝑐𝑑𝑒𝑓𝑔ℎ𝑖𝑗𝑘𝑙𝑚𝑛𝑜𝑝𝑞𝑟𝑠𝑡𝑢𝑣𝑤𝑥𝑦𝑧𝐴𝐵𝐶𝐷𝐸𝐹𝐺𝐻𝐼𝐽𝐾𝐿𝑀𝑁𝑂𝑃𝑄𝑅𝑆𝑇𝑈𝑉𝑊𝑋𝑌𝑍"),
        ("Math Bold Italic", "𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛𝑨𝑩𝑪𝑫𝑬𝑭𝑮𝑯𝑰𝑱𝑲𝑳𝑴𝑵𝑶𝑷𝑸𝑹𝑺𝑻𝑼𝑽𝑾𝑿𝒀𝒁"),
        ("Greek / Pseudo", "αвc∂εƒgнιjкℓмησpqяsтuvwxүzΑΒC∂ƐƑGHIJKLMΠOΡQЯSƬUVWXYZ"),
        ("Small Caps", "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"),
        ("Pseudo-Cyrillic", "авсdёfghїjкlмиорqѓsтцvшхyzАВCДЄFGHІJКLМИОРQЯSТЦVШХYZ"),
        ("Reversed", "ɒdɔbɘᎸǫʜiꞁʞlmnoqrsƚuvwxyzAᙠƆᗡƎꟻGHIJK⅃MИOꟼỌЯƧTUVWXYƸ"),
        ("Sorcerer / Magic", "ค๒ς๔єŦﻮђเןкɭ๓ภ๏קợгรՇยשฬאץչค๒ς๔єŦﻮђเןкɭ๓ภ๏קợгรՇยשฬאץչ"),
        ("Squiggles", "ąҍçժҽƒցհíյklmnօpqɾsԵuvwxվzABÇDΣFGHÍJKLMNOPQRSTUVWXYZ"),
        ("Currency", "₳฿₵Đ€₣₲ⱧłJ₭Ⱡ₥₦Ø₱QⱤ₴₮ɄV₩ӾɎⱫ₳฿₵Đ€₣₲ⱧłJ₭Ⱡ₥₦Ø₱QⱤ₴₮ɄV₩ӾɎⱫ"),
        ("Parenthesized", "⒜⒝⒞⒟⒠⒡⒢⒣⒤⒥⒦⒧⒨⒩⒪⒫⒬⒭⒮⒯⒰⒱⒲⒳⒴⒵🄐🄑🄒🄓🄔🄕🄖🄗🄘🄙🄚🄛🄜🄝🄞🄟🄠🄡🄢🄣🄤🄥🄦🄧🄨🄩"),
        ("Asian / Thick", "卂乃匚刀乇下长卄工丁长乚从𠘨口尸Q尺丂丅凵リ山乂丫乙卂乃匚刀乇下长卄工丁长乚从𠘨口尸Q尺丂丅凵リ山乂丫乙"),
    ]

    res_nums = []
    res_no_nums = []
    res_fx = []

    for name, font_str in FONTS_62:
        if len(font_str) == len(NORMAL_62):
            trans = str.maketrans(NORMAL_62, font_str)
            res_nums.append((name, text.translate(trans)))

    upside_normal = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!?.,'\"()[]{}<>"
    upside_mapped = "ɐqɔpǝɟƃɥıɾʞlɯuodbɹsʇnʌʍxʎz∀ᗺƆᗡƎℲ⅁HIſʞ˥WNOԀΌᖱS⊥∩ΛMX⅄Z0ƖᄅƐㄣϛ9ㄥ86¡¿˙',„)(][}{><"
    if len(upside_normal) == len(upside_mapped):
        up_trans = str.maketrans(upside_normal, upside_mapped)
        res_fx.append(("Upside Down", text.translate(up_trans)[::-1]))

    for name, font_str in FONTS_52:
        if len(font_str) == len(NORMAL_52):
            trans = str.maketrans(NORMAL_52, font_str)
            res_no_nums.append((name, text.translate(trans)))

    over_text = "".join(c + "\u0305" if c.strip() else c for c in text)
    res_fx.append(("Overline (top line)", over_text))

    under_text = "".join(c + "\u0332" if c.strip() else c for c in text)
    res_fx.append(("Underline (underlined)", under_text))

    double_under_text = "".join(c + "\u0333" if c.strip() else c for c in text)
    res_fx.append(("Double Underline", double_under_text))

    zalgo_chars = [chr(i) for i in range(0x0300, 0x036F)]
    z_text = "".join(char + "".join(random.choices(zalgo_chars, k=4)) if char.strip() else char for char in text)
    res_fx.append(("Zalgo / Glitch", z_text))

    tilde_text = "".join(c + "\u033e" if c.strip() else c for c in text)
    res_fx.append(("Tilde Strike", tilde_text))

    dotted_text = "".join(c + "\u0323" if c.strip() else c for c in text)
    res_fx.append(("Dotted underlined", dotted_text))

    cross_text = "".join(c + "\u0353" if c.strip() else c for c in text)
    res_fx.append(("Cross Strike", cross_text))

    asterisk_text = "".join(c + "\u0359" if c.strip() else c for c in text)
    res_fx.append(("Snow / Asterisk Below", asterisk_text))

    wavy_text = "".join(c + "\u0330" if c.strip() else c for c in text)
    res_fx.append(("Wavy underlined", wavy_text))

    sun_text = "".join(c + "\u0489" if c.strip() else c for c in text)
    res_fx.append(("Sun / Magic", sun_text))

    strike_text = "".join(c + "\u0336" if c.strip() else c for c in text)
    res_fx.append(("Strikethrough (crossed out)", strike_text))

    slash_text = "".join(c + "\u0338" if c.strip() else c for c in text)
    res_fx.append(("Slash Through", slash_text))

    diamond_text = "".join(c + "\u20df" if c.strip() else c for c in text)
    res_fx.append(("Diamond Enclosed", diamond_text))

    prohibited_text = "".join(c + "\u20e0" if c.strip() else c for c in text)
    res_fx.append(("Prohibited (no symbol)", prohibited_text))

    box_text = "".join(c + "\u20de" if c.strip() else c for c in text)
    res_fx.append(("Box Enclosed", box_text))

    spaced_text = " ".join(text)
    res_fx.append(("Spaced (Aesthetic / Kerning)", spaced_text))

    reg_text = "".join(chr(0x1F1E6 + ord(c.lower()) - ord("a")) + " " if "a" <= c.lower() <= "z" else c for c in text)
    res_fx.append(("Regional Indicators (blocks)", reg_text.strip()))

    return res_nums, res_no_nums, res_fx


def generate_braille_4x3(text):
    BRAILLE_4X3_DICT = {
        "A": ["⣤⡛⡛⣤", "⣿⡶⡶⣿", "⣿⡀⡀⣿"],
        "B": ["⣿⡛⡛⣤", "⣿⡶⡶⣿", "⣿⣤⣤⡛"],
        "C": ["⣤⡛⡛⡛", "⣿⡀⡀⡀", "⡛⣤⣤⣤"],
        "D": ["⣿⡛⡛⣤", "⣿⡀⡀⣿", "⣿⣤⣤⡛"],
        "E": ["⣿⡛⡛⡛", "⣿⡶⡶⡶", "⣿⣤⣤⣤"],
        "F": ["⣿⡛⡛⡛", "⣿⡶⡶⡀", "⣿⡀⡀⡀"],
        "G": ["⣤⡛⡛⡛", "⣿⡀⣤⣤", "⡛⣤⣤⣿"],
        "H": ["⣿⡀⡀⣿", "⣿⡶⡶⣿", "⣿⡀⡀⣿"],
        "I": ["⡛⣻⡟⡛", "⡀⣸⡇⡀", "⣤⣼⣧⣤"],
        "J": ["⡛⡛⣿⡛", "⡀⡀⣿⡀", "⣤⣤⣿⡀"],
        "K": ["⣿⡀⣤⡛", "⣿⡶⡀⡀", "⣿⡀⡛⣤"],
        "L": ["⣿⡀⡀⡀", "⣿⡀⡀⡀", "⣿⣤⣤⣤"],
        "M": ["⣿⣄⣠⣿", "⣿⡘⡃⣿", "⣿⡀⡀⣿"],
        "N": ["⣿⡀⡀⣿", "⣿⣿⡀⣿", "⣿⡀⣿⣿"],
        "O": ["⣤⡛⡛⣤", "⣿⡀⡀⣿", "⡛⣤⣤⡛"],
        "P": ["⣿⡛⡛⣤", "⣿⡶⡶⡛", "⣿⡀⡀⡀"],
        "Q": ["⣤⡛⡛⣤", "⣿⡀⡀⣿", "⡛⣤⣿⣿"],
        "R": ["⣿⡛⡛⣤", "⣿⣤⣤⡛", "⣿⡀⡛⣤"],
        "S": ["⣤⡛⡛⡛", "⡛⡶⡶⣤", "⣤⣤⣤⡛"],
        "T": ["⡛⣻⡟⡛", "⡀⣸⡇⡀", "⡀⣸⡇⡀"],
        "U": ["⣿⡀⡀⣿", "⣿⡀⡀⣿", "⡛⣤⣤⡛"],
        "V": ["⣿⡀⡀⣿", "⣸⡇⣸⡇", "⡀⣸⡇⡀"],
        "W": ["⣿⡀⡀⣿", "⣿⣸⡇⣿", "⣸⡇⣸⡇"],
        "X": ["⣻⣄⣠⡟", "⡀⣹⣏⡀", "⣼⡋⡙⣧"],
        "Y": ["⣿⡀⡀⣿", "⡘⣣⡜⡃", "⡀⣸⡇⡀"],
        "Z": ["⡛⡛⡛⣿", "⡀⣤⡛⡀", "⣿⣤⣤⣤"],
        "0": ["⣿⡛⡛⣿", "⣿⡀⡀⣿", "⣿⣤⣤⣿"],
        "1": ["⡀⡀⡀⣿", "⡀⡀⡀⣿", "⡀⡀⡀⣿"],
        "2": ["⡛⡛⡛⣿", "⣶⡶⡶⡿", "⣿⣤⣤⣤"],
        "3": ["⡛⡛⡛⣿", "⡶⡶⡶⣿", "⣤⣤⣤⣿"],
        "4": ["⣿⡀⡀⣿", "⡿⡶⡶⣿", "⡀⡀⡀⣿"],
        "5": ["⣿⡛⡛⡛", "⡿⡶⡶⣶", "⣤⣤⣤⣿"],
        "6": ["⣿⡛⡛⡛", "⣿⡶⡶⣶", "⣿⣤⣤⣿"],
        "7": ["⡛⡛⡛⣿", "⡀⡀⡀⣿", "⡀⡀⡀⣿"],
        "8": ["⣿⡛⡛⣿", "⣿⡶⡶⣿", "⣿⣤⣤⣿"],
        "9": ["⣿⡛⡛⣿", "⡿⡶⡶⣿", "⣤⣤⣤⣿"],
        ".": ["⡀⡀⡀⡀", "⡀⡀⡀⡀", "⡀⣶⡀⡀"],
        ",": ["⡀⡀⡀⡀", "⡀⡀⡀⡀", "⡀⣤⡛⡀"],
        ":": ["⡀⣶⡀⡀", "⡀⡀⡀⡀", "⡀⣶⡀⡀"],
        ";": ["⡀⣶⡀⡀", "⡀⡀⡀⡀", "⡀⣤⡛⡀"],
        "?": ["⣤⡛⡛⣤", "⡀⣤⡶⡛", "⡀⣤⡀⡀"],
        "!": ["⡀⣿⡀⡀", "⡀⣿⡀⡀", "⡀⣤⡀⡀"],
        "_": ["⡀⡀⡀⡀", "⡀⡀⡀⡀", "⣤⣤⣤⣤"],
        "-": ["⡀⡀⡀⡀", "⡶⡶⡶⡶", "⡀⡀⡀⡀"],
        "+": ["⡀⣰⡆⡀", "⡶⣾⡷⡶", "⡀⡸⡇⡀"],
        "/": ["⡀⡀⣠⡟", "⡀⣰⡏⡀", "⣼⡃⡀⡀"],
        " ": ["⡀⡀⡀⡀", "⡀⡀⡀⡀", "⡀⡀⡀⡀"],
    }

    line1, line2, line3 = "", "", ""
    for char in text.upper():
        if char in BRAILLE_4X3_DICT:
            block = BRAILLE_4X3_DICT[char]
        else:
            block = BRAILLE_4X3_DICT[" "]

        line1 += "⡀" + block[0]
        line2 += "⡀" + block[1]
        line3 += "⡀" + block[2]

    line1 += "⡀"
    line2 += "⡀"
    line3 += "⡀"

    return f"{line1}\n{line2}\n{line3}"


def generate_block_4x3(text):
    BLOCK_4X3_DICT = {
        "A": ["█▀▀█", "█▀▀█", "█▁▁█"],
        "B": ["█▀▀▄", "█▀▀█", "█▄▄▀"],
        "C": ["▄▀▀▀", "█▁▁▁", "▀▄▄▄"],
        "D": ["█▀▀▄", "█▁▁█", "█▄▄▀"],
        "E": ["█▀▀▀", "█▀▀▀", "█▄▄▄"],
        "F": ["█▀▀▀", "█▀▀▁", "█▁▁▁"],
        "G": ["▄▀▀▀", "█▁▄▄", "▀▄▄█"],
        "H": ["█▁▁█", "█▀▀█", "█▁▁█"],
        "I": ["▀▜▛▀", "▁▐▌▁", "▄▟▙▄"],
        "J": ["▀▀█▀", "▁▁█▁", "▄▄█▁"],
        "K": ["█▁▄▀", "██▁▁", "█▁▀▄"],
        "L": ["█▁▁▁", "█▁▁▁", "█▄▄▄"],
        "M": ["█▄▄█", "█▝▘█", "█▁▁█"],
        "N": ["█▁▁█", "██▁█", "█▁██"],
        "O": ["▄▀▀▄", "█▁▁█", "▀▄▄▀"],
        "P": ["█▀▀▄", "█▀▀▁", "█▁▁▁"],
        "Q": ["▄▀▀▄", "█▁▁█", "▀▄██"],
        "R": ["█▀▀▄", "█▄▄▀", "█▁▀▄"],
        "S": ["▄▀▀▀", "▀▀▀▄", "▄▄▄▀"],
        "T": ["▀▜▛▀", "▁▐▌▁", "▁▐▌▁"],
        "U": ["█▁▁█", "█▁▁█", "▀▄▄▀"],
        "V": ["█▁▁█", "▐▌▐▌", "▁▐▌▁"],
        "W": ["█▁▁█", "█▐▌█", "▐▌▐▌"],
        "X": ["▜▖▗▛", "▁▐▌▁", "▟▘▝▙"],
        "Y": ["█▁▁█", "▝▚▞▘", "▁▐▌▁"],
        "Z": ["▀▀▀█", "▁▄▀▁", "█▄▄▄"],
        "0": ["█▀▀█", "█▁▁█", "▀▄▄▀"],
        "1": ["▁▁▁█", "▁▁▁█", "▁▁▁█"],
        "2": ["▀▀▀█", "█▀▀▀", "█▄▄▄"],
        "3": ["▀▀▀█", "▀▀▀█", "▄▄▄█"],
        "4": ["█▁▁█", "▀▀▀█", "▁▁▁█"],
        "5": ["█▀▀▀", "▀▀▀█", "▄▄▄█"],
        "6": ["█▀▀▀", "█▀▀█", "█▄▄█"],
        "7": ["▀▀▀█", "▁▁▁█", "▁▁▁█"],
        "8": ["█▀▀█", "█▀▀█", "█▄▄█"],
        "9": ["█▀▀█", "▀▀▀█", "▄▄▄█"],
        ".": ["▁▁▁▁", "▁▁▁▁", "▁█▁▁"],
        ",": ["▁▁▁▁", "▁▁▁▁", "▁▄▀▁"],
        ":": ["▁█▁▁", "▁▁▁▁", "▁█▁▁"],
        ";": ["▁█▁▁", "▁▁▁▁", "▁▄▀▁"],
        "?": ["▄▀▀▄", "▁▄▀▁", "▁▄▁▁"],
        "!": ["▁█▁▁", "▁█▁▁", "▁▄▁▁"],
        "_": ["▁▁▁▁", "▁▁▁▁", "▄▄▄▄"],
        "-": ["▁▁▁▁", "▀▀▀▀", "▁▁▁▁"],
        "+": ["▁▐▌▁", "▀▜▛▀", "▁▐▌▁"],
        "/": ["▁▁▗▛", "▁▐▌▁", "▟▘▁▁"],
        " ": ["▁▁▁▁", "▁▁▁▁", "▁▁▁▁"],
    }

    line1, line2, line3 = "", "", ""
    for char in text.upper():
        if char in BLOCK_4X3_DICT:
            block = BLOCK_4X3_DICT[char]
        else:
            block = BLOCK_4X3_DICT[" "]

        line1 += "▁" + block[0]
        line2 += "▁" + block[1]
        line3 += "▁" + block[2]

    line1 += "▁"
    line2 += "▁"
    line3 += "▁"

    return f"{line1}\n{line2}\n{line3}"


def handle_text_generator_menu():
    while True:
        clear_screen()
        print("=" * WIDTH)
        print("[Text generator with aesthetic typography]".center(WIDTH))
        print("=" * WIDTH)
        print(" Type your text below to generate text to copy & paste")
        print(" Leave blank and press Enter or press Esc to go back...")
        print("=" * WIDTH)

        user_text = input_with_esc("> ")
        if user_text is None or not user_text:
            return

        res_nums, res_no_nums, res_fx = text_generator(user_text)

        print("\n" + "=" * WIDTH)
        print(" [FONTS WITH STYLIZED NUMBERS SUPPORT]".center(WIDTH))
        print("=" * WIDTH)
        for name, f_text in res_nums:
            print(f"  {f_text}  -  {name}")

        print("\n" + "=" * WIDTH)
        print(" [FONTS WITH NORMAL NUMBERS]".center(WIDTH))
        print("=" * WIDTH)
        for name, f_text in res_no_nums:
            print(f"  {f_text}  -  {name}")

        print("\n" + "=" * WIDTH)
        print(" [SPECIAL EFFECTS & DECORATIONS]".center(WIDTH))
        print("=" * WIDTH)
        for name, f_text in res_fx:
            print(f"  {f_text}  -  {name}")

        print("\n" + "=" * WIDTH)
        print(" [BRAILLE DOTS 4X3]".center(WIDTH))
        print("=" * WIDTH)
        print(generate_braille_4x3(user_text))

        print("\n" + "=" * WIDTH)
        print(" [BLOCK ELEMENTS 4X3]".center(WIDTH))
        print("=" * WIDTH)
        print(generate_block_4x3(user_text))

        print("\nPress any key to generate another or ESC to return to main menu...")
        key = wait_for_key()
        if key == "\x1b":
            return


# ==========================================
# WORKSPACE MANIPULATION
# ==========================================


def clean_right_spaces():
    lines = read_workspace_lines(strip_newlines=False)
    if not lines:
        return

    all_invis = " \t\u2800\u2804⠄\u00a0⠠⠂⠐"
    safe_dots = "⠄\u2804⠠⠂⠐"

    new_lines = []
    for line in lines:
        core_line = line.rstrip("\r\n")
        if not core_line:
            new_lines.append("\n")
            continue

        idx = len(core_line) - 1
        while idx >= 0 and core_line[idx] in all_invis:
            idx -= 1

        if idx == -1:
            new_lines.append("\n")
        else:
            keep_idx = idx
            if idx + 1 < len(core_line) and core_line[idx + 1] in safe_dots:
                keep_idx = idx + 1

            new_lines.append(core_line[: keep_idx + 1] + "\n")

    write_workspace_lines(new_lines, append_newline=False)


def crop_left_spaces():
    lines = read_workspace_lines(strip_newlines=False)
    if not lines:
        return

    all_invis = " \t\u2800\u2804⠄\u00a0⠠⠂⠐"
    safe_dots = "⠄\u2804⠠⠂⠐"
    min_indent = float("inf")
    has_content = False

    for line in lines:
        core_line = line.rstrip("\r\n")
        if not core_line:
            continue

        idx = 0
        while idx < len(core_line) and core_line[idx] in all_invis:
            idx += 1

        if idx < len(core_line):
            eff_idx = idx
            if idx > 0 and core_line[idx - 1] in safe_dots:
                eff_idx = idx - 1

            if eff_idx < min_indent:
                min_indent = eff_idx
            has_content = True

    if not has_content or min_indent == float("inf"):
        min_indent = 0

    new_lines = []
    for line in lines:
        core_line = line.rstrip("\r\n")
        if not core_line:
            new_lines.append("\n")
            continue

        idx = 0
        while idx < len(core_line) and core_line[idx] in all_invis:
            idx += 1

        if idx == len(core_line):
            new_lines.append("\n")
        else:
            new_lead_len = idx - min_indent
            if new_lead_len > 0:
                last_invis = core_line[idx - 1]
                if last_invis in safe_dots:
                    new_padding = "\u2800" * (new_lead_len - 1) + last_invis
                else:
                    new_padding = "\u2800" * new_lead_len
            else:
                new_padding = ""

            new_lines.append(new_padding + core_line[idx:] + "\n")

    write_workspace_lines(new_lines, append_newline=False)


def delete_edge(edge, amount):
    lines = read_workspace_lines(strip_newlines=False)
    if not lines or amount <= 0:
        return

    if edge == "t":
        lines = lines[amount:]
    elif edge == "b":
        lines = lines[:-amount] if amount < len(lines) else []
    elif edge == "l":
        lines = [line[amount:] if len(line.rstrip("\r\n")) > 0 else line for line in lines]
    elif edge == "r":
        new_lines = []
        for line in lines:
            has_newline = line.endswith("\n")
            core_line = line.rstrip("\r\n")
            core_line = core_line[:-amount] if len(core_line) > amount else ""
            new_lines.append(core_line + ("\n" if has_newline else ""))
        lines = new_lines

    write_workspace_lines(lines, append_newline=False)


def add_padding(edge, amount):
    lines = read_workspace_lines(strip_newlines=True)
    if not lines:
        return

    pad_char = "\u2800"

    max_len = max((len(line) for line in lines), default=0)
    if max_len == 0:
        max_len = 1

    normalized_lines = [line.ljust(max_len, pad_char) for line in lines]

    new_lines = []
    if edge == "t":
        new_lines = [pad_char * max_len] * amount + normalized_lines
    elif edge == "b":
        new_lines = normalized_lines + [pad_char * max_len] * amount
    elif edge == "l":
        new_lines = [(pad_char * amount) + line for line in normalized_lines]
    elif edge == "r":
        new_lines = [line + (pad_char * amount) for line in normalized_lines]

    write_workspace_lines(new_lines)


# ==========================================
# BRAILLE MANIPULATION
# ==========================================


def keyboard_menu(val):
    if not val:
        return None
    val = val.lower().strip()
    if val == "n":
        return None

    offset = 0
    if "a1" in val:
        offset |= 0x01
    if "a2" in val:
        offset |= 0x02
    if "a3" in val:
        offset |= 0x04
    if "a4" in val:
        offset |= 0x40
    if "b1" in val:
        offset |= 0x08
    if "b2" in val:
        offset |= 0x10
    if "b3" in val:
        offset |= 0x20
    if "b4" in val:
        offset |= 0x80

    if offset == 0:
        return None
    return offset


def swap_characters(old_char, new_char):
    content = read_workspace_content()
    if content is None:
        return
    write_workspace_content(content.replace(old_char, new_char))


def swap_right_to_left():
    content = read_workspace_content()
    if content is None:
        return

    new_content = []
    for char in content:
        if len(char) == 1 and 0x2801 <= ord(char) <= 0x28FF:
            offset = ord(char) - 0x2800
            if (offset & ~0xB8) == 0 and offset > 0:
                new_offset = 0
                if offset & 0x08:
                    new_offset |= 0x01
                if offset & 0x10:
                    new_offset |= 0x02
                if offset & 0x20:
                    new_offset |= 0x04
                if offset & 0x80:
                    new_offset |= 0x40
                new_content.append("\u00a0" + chr(0x2800 + new_offset))
                continue
        new_content.append(char)

    write_workspace_content("".join(new_content))


def revert_swap_right_to_left():
    content = read_workspace_content()
    if content is None:
        return

    new_content = []
    i = 0
    while i < len(content):
        if content[i] == "\u00a0" and i + 1 < len(content):
            next_char = content[i + 1]
            if 0x2801 <= ord(next_char) <= 0x28FF:
                offset = ord(next_char) - 0x2800
                if (offset & ~0x47) == 0 and offset > 0:
                    new_offset = 0
                    if offset & 0x01:
                        new_offset |= 0x08
                    if offset & 0x02:
                        new_offset |= 0x10
                    if offset & 0x04:
                        new_offset |= 0x20
                    if offset & 0x40:
                        new_offset |= 0x80
                    new_content.append(chr(0x2800 + new_offset))
                    i += 2
                    continue
        new_content.append(content[i])
        i += 1

    write_workspace_content("".join(new_content))


def alternate_braille_spaces(mode, include_existing, alt_char, alt_offset):
    lines = read_workspace_lines(strip_newlines=False)
    if not lines:
        return

    new_lines = []
    for row_idx, line in enumerate(lines):
        has_newline = line.endswith("\n")
        core_line = line.rstrip("\r\n")

        new_line = []
        for col_idx, char in enumerate(core_line):
            condition = col_idx % 2 == 0 if mode == 1 else (row_idx + col_idx) % 2 == 0

            if char == "\u2800":
                if condition:
                    new_line.append(alt_char)
                else:
                    new_line.append("\u2800")
            elif include_existing and condition and len(char) == 1 and 0x2801 <= ord(char) <= 0x28FF:
                offset = ord(char) - 0x2800
                offset |= alt_offset
                new_line.append(chr(0x2800 + offset))
            else:
                new_line.append(char)
        new_lines.append("".join(new_line) + ("\n" if has_newline else ""))

    write_workspace_lines(new_lines, append_newline=False)


def add_left_dot_to_right_braille():
    content = read_workspace_content()
    if content is None:
        return

    new_content = []
    for char in content:
        if len(char) == 1 and 0x2801 <= ord(char) <= 0x28FF:
            offset = ord(char) - 0x2800
            if (offset & ~0xB8) == 0 and offset > 0:
                new_offset = offset
                if offset & 0x08:
                    new_offset |= 0x01
                elif offset & 0x10:
                    new_offset |= 0x02
                elif offset & 0x20:
                    new_offset |= 0x04
                elif offset & 0x80:
                    new_offset |= 0x40
                new_content.append(chr(0x2800 + new_offset))
                continue
        new_content.append(char)

    write_workspace_content("".join(new_content))


def add_custom_to_all_braille(added_offset):
    content = read_workspace_content()
    if content is None:
        return

    new_content = []
    for char in content:
        if len(char) == 1 and 0x2801 <= ord(char) <= 0x28FF:
            offset = ord(char) - 0x2800
            offset |= added_offset
            new_content.append(chr(0x2800 + offset))
        else:
            new_content.append(char)

    write_workspace_content("".join(new_content))


def invert_all_braille():
    content = read_workspace_content()
    if content is None:
        return

    new_content = []
    for char in content:
        if len(char) == 1 and 0x2800 <= ord(char) <= 0x28FF:
            offset = ord(char) - 0x2800
            new_offset = offset ^ 0xFF
            new_content.append(chr(0x2800 + new_offset))
        else:
            new_content.append(char)

    write_workspace_content("".join(new_content))


def flip_braille_char(char, direction):
    if not (len(char) == 1 and 0x2800 <= ord(char) <= 0x28FF):
        return char
    offset = ord(char) - 0x2800
    new_offset = 0
    if direction == "h":
        if offset & 0x01:
            new_offset |= 0x08
        if offset & 0x08:
            new_offset |= 0x01
        if offset & 0x02:
            new_offset |= 0x10
        if offset & 0x10:
            new_offset |= 0x02
        if offset & 0x04:
            new_offset |= 0x20
        if offset & 0x20:
            new_offset |= 0x04
        if offset & 0x40:
            new_offset |= 0x80
        if offset & 0x80:
            new_offset |= 0x40
    elif direction == "v":
        if offset & 0x01:
            new_offset |= 0x40
        if offset & 0x40:
            new_offset |= 0x01
        if offset & 0x08:
            new_offset |= 0x80
        if offset & 0x80:
            new_offset |= 0x08
        if offset & 0x02:
            new_offset |= 0x04
        if offset & 0x04:
            new_offset |= 0x02
        if offset & 0x10:
            new_offset |= 0x20
        if offset & 0x20:
            new_offset |= 0x10
    return chr(0x2800 + new_offset)


def flip_workspace(direction):
    lines = read_workspace_lines()
    if not lines:
        return

    new_lines = []
    if direction == "h":
        max_len = max((len(line) for line in lines), default=0)
        padded_lines = [line.ljust(max_len, "\u2800") for line in lines]

        for line in padded_lines:
            new_line = "".join(flip_braille_char(c, "h") for c in reversed(line))
            new_lines.append(new_line)

    elif direction == "v":
        for line in reversed(lines):
            new_line = "".join(flip_braille_char(c, "v") for c in line)
            new_lines.append(new_line)

    write_workspace_lines(new_lines)


def mirror_workspace(axis, amount):
    lines = read_workspace_lines()
    if not lines:
        return

    if axis == "c":
        max_len = max((len(line) for line in lines), default=0)
        padded_lines = [line.ljust(max_len, "\u2800") for line in lines]
        new_lines = []
        for line in padded_lines:
            if amount >= max_len:
                mirrored = "".join(flip_braille_char(c, "h") for c in reversed(line))
                new_lines.append(mirrored)
            else:
                left_part = line[:amount]
                mirrored = "".join(flip_braille_char(c, "h") for c in reversed(left_part))
                core_part = line[: max_len - amount]
                new_lines.append(core_part + mirrored)
        lines = new_lines

    elif axis == "l":
        if amount >= len(lines):
            mirrored = ["".join(flip_braille_char(c, "v") for c in line) for line in reversed(lines)]
            lines = mirrored
        else:
            top_part = lines[:amount]
            mirrored = ["".join(flip_braille_char(c, "v") for c in line) for line in reversed(top_part)]
            lines = lines[: len(lines) - amount] + mirrored

    write_workspace_lines(lines)


# ==========================================
# EFFECTS
# ==========================================


def rain_effect(pct_affected):
    lines = read_workspace_lines()
    if not lines:
        return

    max_len = max((len(line) for line in lines), default=0)
    padded_lines = [line.ljust(max_len, "\u2800") for line in lines]

    columns = []
    threshold = pct_affected / 100.0
    for col_idx in range(max_len):
        col_chars = [line[col_idx] for line in padded_lines]
        shift = 1 if random.random() < threshold else 0

        if shift > 0:
            col_chars = ["\u2800"] * shift + col_chars[:-shift]
        columns.append(col_chars)

    new_lines = []
    for row_idx in range(len(padded_lines)):
        row_str = "".join(columns[col_idx][row_idx] for col_idx in range(max_len))
        new_lines.append(row_str)

    write_workspace_lines(new_lines)


def earthquake_effect(pct_affected):
    lines = read_workspace_lines()
    if not lines:
        return

    new_lines = []
    chance = pct_affected / 2.0
    stay_chance = 100.0 - pct_affected

    for line in lines:
        shift = random.choices([-1, 0, 1], weights=[chance, stay_chance, chance])[0]
        if shift > 0:
            new_lines.append("\u2800" * shift + line)
        elif shift < 0:
            new_lines.append(line[-shift:])
        else:
            new_lines.append(line)

    write_workspace_lines(new_lines)


def glitch_effect(pct_affected):
    content = read_workspace_content()
    if content is None:
        return

    new_content = []
    threshold = pct_affected / 100.0

    for char in content:
        if len(char) == 1 and 0x2801 <= ord(char) <= 0x28FF:
            if random.random() < threshold:
                offset = ord(char) - 0x2800
                mask = random.choice([0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80])
                new_offset = offset ^ mask
                new_content.append(chr(0x2800 + new_offset))
            else:
                new_content.append(char)
        else:
            new_content.append(char)

    write_workspace_content("".join(new_content))


# ==========================================
# HIDDEN UNICODE WATERMARK
# ==========================================


def text_to_hidden_unicode(text):
    words = text.split(" ")
    encoded_words = []
    for word in words:
        bin_word = "".join(format(byte, "08b") for byte in word.encode("utf-8"))
        hidden_word = bin_word.replace("0", "\u200b").replace("1", "\u200c")
        encoded_words.append(hidden_word)
    return "\u200d".join(encoded_words)


def hidden_unicode_to_text(hidden_str):
    words = hidden_str.split("\u200d")
    decoded_text = []
    for word in words:
        bin_str = word.replace("\u200b", "0").replace("\u200c", "1")
        byte_array = bytearray()
        for i in range(0, len(bin_str), 8):
            chunk = bin_str[i : i + 8]
            if len(chunk) == 8:
                try:
                    byte_array.append(int(chunk, 2))
                except ValueError:
                    pass
        try:
            decoded_text.append(byte_array.decode("utf-8"))
        except UnicodeDecodeError:
            decoded_text.append("?")
    return " ".join(decoded_text)


def read_hidden_text():
    content = read_workspace_content()
    if content is None:
        return

    matches = re.findall(r"[\u200B\u200C\u200D]+", content)

    found_valid = False
    for match in matches:
        if len(match) >= 2:
            decoded = hidden_unicode_to_text(match)
            if decoded.strip():
                chars_len = len(match)
                bytes_len = len(match.encode("utf-8"))
                print(f"[*] Hidden text found: {decoded}")
                print(f"    Information: {chars_len} chars, {bytes_len} bytes")
                found_valid = True

    if not found_valid:
        print("[-] No hidden texts found in the workspace")

    print("\nPress any key to go back...")
    wait_for_key()


def add_hidden_text():
    lines = read_workspace_lines()
    if not lines:
        return False

    print(" Type the text you want to encode and hide as a watermark")
    print(" Leave blank and press Enter or press Esc to go back...")
    text = input_with_esc("> ")
    if text is None or not text.strip():
        return False
    text = text.strip()

    hidden_str = text_to_hidden_unicode(text)

    mid_y = len(lines) // 2
    mid_line = lines[mid_y]
    mid_x = len(mid_line) // 2

    lines[mid_y] = mid_line[:mid_x] + hidden_str + mid_line[mid_x:]
    write_workspace_lines(lines)
    return True


def delete_hidden_text():
    content = read_workspace_content()
    if content is None:
        return False

    new_content = re.sub(r"[\u200B\u200C\u200D]", "", content)
    write_workspace_content(new_content)
    return True


def handle_hidden_menu():
    made_changes = False
    while True:
        clear_screen()
        print("=" * WIDTH)
        print("[Hidden Unicode texts menu]".center(WIDTH))
        print("=" * WIDTH)
        print(" Note: Binary encryption using invisible Zero-Width characters")
        print(" to act as a hidden watermark\n")
        print(" U+200B='0', U+200C='1'")
        print(" U+200D is used as a 'Space' to save 8 binary characters per gap")
        print(" Letter is 8 binary digits")
        print(" Invisible character uses 3 bytes")
        print(" Total: 24 bytes for each letter added")
        print("=" * WIDTH)
        print("- R to Read hidden Unicode texts")
        print("- A to Add hidden Unicode texts in the center")
        print("- D to Delete hidden Unicode texts sets")
        print("\nPress ESC to go back...")

        key = wait_for_key()

        if key == "\x1b":
            return made_changes
        elif key.lower() == "r":
            print()
            read_hidden_text()
        elif key.lower() == "a":
            print()
            if add_hidden_text():
                made_changes = True
        elif key.lower() == "d":
            print()
            if prompt_yn("[!] Confirm deleting all hidden Unicode sets? [Y/n]: "):
                if delete_hidden_text():
                    made_changes = True


# ==========================================
# KEYBOARD MENU
# ==========================================

MORSE_CODE_DICT = {"A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--", "Z": "--..", "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.", ".": ".-.-.-", ",": "--..--", "?": "..--..", "'": ".----.", "!": "-.-.--", "/": "-..-.", "(": "-.--.", ")": "-.--.-", "&": ".-...", ":": "---...", ";": "-.-.-.", "=": "-...-", "+": ".-.-.", "-": "-....-", "_": "..--.-", '"': ".-..-.", "$": "...-..-", "@": ".--.-.", "Á": ".--.-", "É": "..-..", "Ñ": "--.--", "Ó": "---.", "Í": "..", "Ú": "..--"}


def copy_text_to_clipboard(text):
    try:
        import pyperclip

        pyperclip.copy(text)
        print(f"\n RESULT: {text}\n [*] Copied to clipboard")
    except ImportError:
        print(f"\n RESULT: {text}\n [!] 'pyperclip' missing, copy manually")
    except Exception:
        print(f"\n RESULT: {text}\n [!] Copy failed, copy manually")


def text_to_binary(text):
    return " ".join(format(byte, "08b") for byte in text.encode("utf-8"))


def binary_to_text(binary):
    try:
        binary = binary.replace(" ", "")
        bytes_list = [int(binary[i : i + 8], 2) for i in range(0, len(binary), 8)]
        return bytearray(bytes_list).decode("utf-8")
    except Exception:
        return "[!] Invalid binary format"


def text_to_morse(text):
    morse = []
    for char in text.upper():
        if char == " ":
            morse.append("/")
        elif char in MORSE_CODE_DICT:
            morse.append(MORSE_CODE_DICT[char])
        else:
            morse.append(char)
    return " ".join(morse)


def morse_to_text(morse_code):
    REVERSE_MORSE = {value: key for key, value in MORSE_CODE_DICT.items()}
    decoded_text = []
    chars = morse_code.split()
    for c in chars:
        if c == "/":
            decoded_text.append(" ")
        elif c in REVERSE_MORSE:
            decoded_text.append(REVERSE_MORSE[c])
        else:
            decoded_text.append(c)
    return "".join(decoded_text).lower()


def handle_morse_code():
    while True:
        clear_screen()
        print("=" * WIDTH)
        print("[Morse code]".center(WIDTH))
        print("=" * WIDTH)
        print("- C to Convert Text to Morse")
        print("- T to Translate Morse to Text")
        print("\nPress ESC to go back...")

        key = wait_for_key()

        if key == "\x1b":
            return
        elif key.lower() == "c":
            print()
            print(" Enter text to convert to Morse [Esc to cancel]:")
            print("=" * WIDTH)
            text = input_with_esc("> ")
            if text:
                res = text_to_morse(text)
                copy_text_to_clipboard(res)
                print("\nPress any key to continue...")
                wait_for_key()
        elif key.lower() == "t":
            print()
            print(" Enter Morse code to translate to text [Esc to cancel]:")
            print("=" * WIDTH)
            morse = input_with_esc("> ")
            if morse:
                res = morse_to_text(morse)
                copy_text_to_clipboard(res)
                print("\nPress any key to continue...")
                wait_for_key()


def handle_binary_code():
    while True:
        clear_screen()
        print("=" * WIDTH)
        print("[Binary code]".center(WIDTH))
        print("=" * WIDTH)
        print("- C to Convert Text to Binary")
        print("- T to Translate Binary to Text")
        print("\nPress ESC to go back...")

        key = wait_for_key()

        if key == "\x1b":
            return
        elif key.lower() == "c":
            print()
            print(" Enter text to convert to Binary [Esc to cancel]:")
            print("=" * WIDTH)
            text = input_with_esc("> ")
            if text:
                res = text_to_binary(text)
                copy_text_to_clipboard(res)
                print("\nPress any key to continue...")
                wait_for_key()
        elif key.lower() == "t":
            print()
            print(" Enter Binary code to translate to text [Esc to cancel]:")
            print("=" * WIDTH)
            binary = input_with_esc("> ")
            if binary:
                res = binary_to_text(binary)
                copy_text_to_clipboard(res)
                print("\nPress any key to continue...")
                wait_for_key()


# ==========================================
# CLASSIC BRAILLE TRANSLATOR
# ==========================================

CLASSIC_BRAILLE_DICT = {"A": "⠁", "B": "⠃", "C": "⠉", "D": "⠙", "E": "⠑", "F": "⠋", "G": "⠛", "H": "⠓", "I": "⠊", "J": "⠚", "K": "⠅", "L": "⠇", "M": "⠍", "N": "⠝", "O": "⠕", "P": "⠏", "Q": "⠟", "R": "⠗", "S": "⠎", "T": "⠞", "U": "⠥", "V": "⠧", "W": "⠺", "X": "⠭", "Y": "⠽", "Z": "⠵", " ": " ", "1": "⠼⠁", "2": "⠼⠃", "3": "⠼⠉", "4": "⠼⠙", "5": "⠼⠑", "6": "⠼⠋", "7": "⠼⠛", "8": "⠼⠓", "9": "⠼⠊", "0": "⠼⠚", ",": "⠂", ";": "⠆", ":": "⠒", ".": "⠲", "?": "⠦", "!": "⠖", "-": "⠤", "(": "⠐⠣", ")": "⠐⠜"}


def text_to_classic_braille(text):
    result = []
    in_number = False
    for char in text.upper():
        if char.isdigit():
            if not in_number:
                result.append("⠼")
                in_number = True
            digit_map = {"1": "⠁", "2": "⠃", "3": "⠉", "4": "⠙", "5": "⠑", "6": "⠋", "7": "⠛", "8": "⠓", "9": "⠊", "0": "⠚"}
            result.append(digit_map[char])
        else:
            if char != " ":
                in_number = False
            if char in CLASSIC_BRAILLE_DICT:
                result.append(CLASSIC_BRAILLE_DICT[char])
            else:
                result.append(char)
    return "".join(result)


def classic_braille_to_text(braille):
    REVERSE_BRAILLE = {"⠁": "A", "⠃": "B", "⠉": "C", "⠙": "D", "⠑": "E", "⠋": "F", "⠛": "G", "⠓": "H", "⠊": "I", "⠚": "J", "⠅": "K", "⠇": "L", "⠍": "M", "⠝": "N", "⠕": "O", "⠏": "P", "⠟": "Q", "⠗": "R", "⠎": "S", "⠞": "T", "⠥": "U", "⠧": "V", "⠺": "W", "⠭": "X", "⠽": "Y", "⠵": "Z", " ": " ", "⠂": ",", "⠆": ";", "⠒": ":", "⠲": ".", "⠦": "?", "⠖": "!", "⠤": "-", "⠣": "(", "⠜": ")"}
    DIGIT_MAP = {"⠁": "1", "⠃": "2", "⠉": "3", "⠙": "4", "⠑": "5", "⠋": "6", "⠛": "7", "⠓": "8", "⠊": "9", "⠚": "0"}

    result = []
    i = 0
    while i < len(braille):
        char = braille[i]
        if char == "⠼":
            i += 1
            while i < len(braille) and braille[i] in DIGIT_MAP:
                result.append(DIGIT_MAP[braille[i]])
                i += 1
            continue
        elif char == "⠐" and i + 1 < len(braille):
            next_char = braille[i + 1]
            if next_char == "⠣":
                result.append("(")
                i += 2
                continue
            elif next_char == "⠜":
                result.append(")")
                i += 2
                continue

        if char in REVERSE_BRAILLE:
            result.append(REVERSE_BRAILLE[char])
        else:
            result.append(char)
        i += 1
    return "".join(result).lower()


def handle_classic_braille():
    while True:
        clear_screen()
        print("=" * WIDTH)
        print("[Classic Braille dots]".center(WIDTH))
        print("=" * WIDTH)
        print("- C to Convert Text to Braille")
        print("- T to Translate Braille to Text")
        print("\nPress ESC to go back...")

        key = wait_for_key()

        if key == "\x1b":
            return
        elif key.lower() == "c":
            print()
            print(" Enter text to convert to Classic Braille [Esc to cancel]:")
            print("=" * WIDTH)
            text = input_with_esc("> ")
            if text:
                res = text_to_classic_braille(text)
                copy_text_to_clipboard(res)
                print("\nPress any key to continue...")
                wait_for_key()
        elif key.lower() == "t":
            print()
            print(" Enter Classic Braille to translate to text [Esc to cancel]:")
            print("=" * WIDTH)
            braille = input_with_esc("> ")
            if braille:
                res = classic_braille_to_text(braille)
                copy_text_to_clipboard(res)
                print("\nPress any key to continue...")
                wait_for_key()


def handle_braille_keyboard():
    global braille_history

    try:
        import pyperclip

        has_clipboard = True
    except ImportError:
        has_clipboard = False

    while True:
        clear_screen()
        print("=" * WIDTH)
        print("[Braille keyboard input]".center(WIDTH))
        if has_clipboard:
            print("[!] CAUTION: Typing here instantly overwrites your clipboard".center(WIDTH))
        else:
            print("[!] Not found 'pyperclip' to enable Auto-copy".center(WIDTH))
        print("=" * WIDTH)

        def pad(text):
            return f" {text}"[:HALF_WIDTH].ljust(HALF_WIDTH)

        print(pad("[Coordinate map]") + "│" + pad("Type your coordinates like: A1A2B2"))
        print(pad(" A1 ⠁ ⠈ B1") + "│" + pad("Commas for multiple: a1,space,b1b2"))
        print(pad(" A2 ⠂ ⠐ B2") + "│" + pad("Special: type 'space' or 'nbsp'"))
        print(pad(" A3 ⠄ ⠠ B3") + "│" + pad("Block Shades: E1, E2, E3, E4"))
        print(pad(" A4 ⡀ ⢀ B4") + "│" + pad("- H to History log"))
        print(" Leave blank and press Enter or press Esc to go back...")
        print("=" * WIDTH)

        val = input_with_esc("> ")
        if val is None or not val:
            return

        val = val.strip().lower()

        if val == "h":
            clear_screen()
            print("=" * WIDTH)
            print("[History log]".center(WIDTH))
            print("=" * WIDTH)

            try:
                with open("Braille_Shades_Art_history_log.txt", "w", encoding="utf-8") as log_file:
                    log_file.write("=== Braille Shades Art History log ===\n")
                    if not braille_history:
                        log_file.write(" History is empty.\n")
                    else:
                        for i, (b_chars, b_names) in enumerate(braille_history, 1):
                            log_file.write(f" {i}. [⠀{b_chars}⠀] - {b_names}\n")
            except Exception:
                pass

            if not braille_history:
                print(" History is empty.")
            else:
                for i, (b_chars, b_names) in enumerate(braille_history, 1):
                    print(f" {i}. [⠀{b_chars}⠀] - {b_names}")

            print("\n [*] Log generated in 'Braille_Shades_Art_history_log.txt'")

            print("\nPress any key to go back...")
            wait_for_key()
            continue

        parts = [p.strip() for p in val.split(",")]

        result_chars = ""
        names = []
        valid_input = True

        for part in parts:
            if not part:
                continue

            if part == "space":
                result_chars += "\u2800"
                names.append("0x2800")
            elif part == "nbsp":
                result_chars += "\u00a0"
                names.append("0x00a0")
            elif part == "e1":
                result_chars += "\u2588\u2588"
                names.append("0x2588")
            elif part == "e2":
                result_chars += "\u2593\u2593"
                names.append("0x2593")
            elif part == "e3":
                result_chars += "\u2592\u2592"
                names.append("0x2592")
            elif part == "e4":
                result_chars += "\u2591\u2591"
                names.append("0x2591")
            else:
                offset = keyboard_menu(part)

                if offset is None:
                    print(f"\n [!] Invalid input '{part}', use formats like A1A2B1")
                    valid_input = False
                    break

                result_chars += chr(0x2800 + offset)
                names.append(f"{hex(0x2800 + offset)}")
        if not valid_input:
            print("\nPress any key to continue...")
            wait_for_key()
            continue

        if result_chars:
            copy_success = False

            if has_clipboard:
                try:
                    pyperclip.copy(result_chars)
                    print(f"\n RESULT: [⠀{result_chars}⠀]  <-- Copied to clipboard\n")
                    copy_success = True
                except Exception:
                    print("\n [!] Copy failed, copy manually:")
            else:
                print("\n [!] 'pyperclip' missing, copy manually:")

            if not copy_success:
                print(f" RESULT: [⠀{result_chars}⠀]")

            names_joined = ", ".join(names)
            print(f" {names_joined}")

            braille_history.append((result_chars, names_joined))

        print("\n Press any key to generate another...")
        wait_for_key()


def handle_character_sheets():
    while True:
        clear_screen()
        print("=" * WIDTH)
        print("[Character sheets]".center(WIDTH))
        print("=" * WIDTH)
        print("- B to Braille Patterns")
        print("- E to Block Elements")
        print("- D to Box Drawing")
        print("- G to Geometric Shapes")
        print("\nPress ESC to go back...")

        key = wait_for_key()

        if key == "\x1b":
            break
        elif key.lower() == "b":
            clear_screen()
            print("=" * WIDTH)
            print("[Braille Patterns]".center(WIDTH))
            print("=" * WIDTH)
            print(" All Braille, 256 characters (U+2800 - U+28FF): \n")

            for row in range(8):
                line = "⠀"
                for col in range(32):
                    char_idx = (row * 32) + col
                    if char_idx < 256:
                        line += chr(0x2800 + char_idx) + "⠀"
                print(line)

            print("\n Right-dots Braille (15 characters):\n")
            print("⠀⠈⠀⠐⠀⠠⠀⢀⠀⠘⠀⠰⠀⢠⠀⠨⠀⢐⠀⢈⠀⠸⠀⢰⠀⢘⠀⢨⠀⢸")

            print("\nPress any key to go back...")
            wait_for_key()

        elif key.lower() == "e":
            clear_screen()
            print("=" * WIDTH)
            print("[Block Elements]".center(WIDTH))
            print("=" * WIDTH)
            print(" Block Elements, 32 characters (U+2580 - U+259F): \n")

            for row in range(4):
                line = " "
                for col in range(8):
                    char_idx = (row * 8) + col
                    if char_idx < 32:
                        line += chr(0x2580 + char_idx) + " "
                print(line)

            print("\nPress any key to go back...")
            wait_for_key()

        elif key.lower() == "d":
            clear_screen()
            print("=" * WIDTH)
            print("[Box Drawing]".center(WIDTH))
            print("=" * WIDTH)
            print(" Box Drawing, 128 characters (U+2500 - U+257F): \n")

            for row in range(8):
                line = " "
                for col in range(16):
                    char_idx = (row * 16) + col
                    if char_idx < 128:
                        line += chr(0x2500 + char_idx) + " "
                print(line)

            print("\nPress any key to go back...")
            wait_for_key()

        elif key.lower() == "g":
            clear_screen()
            print("=" * WIDTH)
            print("[Geometric Shapes]".center(WIDTH))
            print("=" * WIDTH)
            print(" Geometric Shapes, 96 characters (U+25A0 - U+25FF): \n")

            for row in range(6):
                line = " "
                for col in range(16):
                    char_idx = (row * 16) + col
                    if char_idx < 96:
                        line += chr(0x25A0 + char_idx) + " "
                print(line)

            print("\nPress any key to go back...")
            wait_for_key()


def handle_keyboard_menu():
    while True:
        clear_screen()
        print("=" * WIDTH)
        print("[Keyboard menu]".center(WIDTH))
        print("=" * WIDTH)
        print("- K to Braille Keyboard input")
        print("- S to Character Sheets")
        print("\n- B to Binary code")
        print("- M to Morse code")
        print("- C to Classic Braille dots")
        print("\nPress ESC to go back...")

        key = wait_for_key()

        if key == "\x1b":
            return
        elif key.lower() == "k":
            handle_braille_keyboard()
        elif key.lower() == "s":
            handle_character_sheets()
        elif key.lower() == "b":
            handle_binary_code()
        elif key.lower() == "m":
            handle_morse_code()
        elif key.lower() == "c":
            handle_classic_braille()


# ==========================================
# FILE OPERATIONS
# ==========================================


def generate_blank_workspace():
    write_workspace_content((("\u2800" * 30) + "\n") * 10)


def create_incremental_backup():
    content = read_workspace_content()
    if content is None:
        print(f"\n[!] Error: Cannot backup because '{WORKSPACE_FILE}' does not exist")
        return False

    counter = 1
    while True:
        backup_name = f"Braille_Shades_Art_workspace_backup_{counter}.txt"
        if not os.path.exists(backup_name):
            break
        counter += 1

    with open(backup_name, "w", encoding="utf-8") as bf:
        bf.write(content)

    print(f"\n[!] SUCCESS: Backup saved safely as '{backup_name}'")
    return True


# ==========================================
# MENUS
# ==========================================


def handle_backup_menu():
    made_changes = False
    while True:
        clear_screen()
        print("=" * WIDTH)
        print("[Backup menu]".center(WIDTH))
        print("=" * WIDTH)
        print("- S to Save current workspace incrementally")
        print("- L to Load a backup number")
        print("- D to Delete a backup number")
        print("\nPress ESC to go back...")

        key = wait_for_key()

        if key == "\x1b":
            return made_changes
        elif key.lower() == "s":
            print()
            if prompt_yn("Backup copy of 'Braille_Shades_Art_workspace.txt'? [Y/n]: "):
                if create_incremental_backup():
                    made_changes = True
                print("\nPress any key to continue...")
                wait_for_key()
        elif key.lower() == "l":
            print()
            num = input_number("Enter the backup number to load [N to cancel]: ")
            if num is not None:
                if prompt_yn(f"[!] CAUTION: Loading backup {num} is irreversible [Y/n]: "):
                    backup_name = f"Braille_Shades_Art_workspace_backup_{num}.txt"
                    if os.path.exists(backup_name):
                        with open(backup_name, "r", encoding="utf-8") as bf:
                            write_workspace_content(bf.read())
                        print(f"\n[!] SUCCESS: Backup '{backup_name}' loaded successfully")
                        made_changes = True
                    else:
                        print(f"\n[!] ERROR: Backup file '{backup_name}' not found")
                    print("\nPress any key to continue...")
                    wait_for_key()
        elif key.lower() == "d":
            print()
            num = input_number("Enter the backup number to delete [N to cancel]: ")
            if num is not None:
                backup_name = f"Braille_Shades_Art_workspace_backup_{num}.txt"
                if os.path.exists(backup_name):
                    if prompt_yn(f"[!] CAUTION: Deleting backup {num} is permanent [Y/n]: "):
                        os.remove(backup_name)
                        print(f"\n[!] SUCCESS: Backup '{backup_name}' deleted successfully")
                        made_changes = True
                else:
                    print(f"\n[!] ERROR: Backup file '{backup_name}' not found")
                print("\nPress any key to continue...")
                wait_for_key()


def handle_clean_menu():
    made_changes = False
    while True:
        clear_screen()
        print("=" * WIDTH)
        print("[Clean spaces menu]".center(WIDTH))
        print("=" * WIDTH)
        print("- C to Clean spaces on the right (normal, tab, Braille, ⠄)")
        print("- A to Auto-crop empty spaces on the left margin (normal, tab, Braille, ⠄)")
        print("- B to Both (Clean right and Auto-crop left)")
        print("\nPress ESC to go back...")

        key = wait_for_key()

        if key == "\x1b":
            return made_changes
        elif key.lower() == "c":
            print()
            if prompt_yn("Confirm cleaning right spaces? [Y/n]: "):
                clean_right_spaces()
                made_changes = True
        elif key.lower() == "a":
            print()
            if prompt_yn("Confirm auto-cropping left margin spaces? [Y/n]: "):
                crop_left_spaces()
                made_changes = True
        elif key.lower() == "b":
            print()
            if prompt_yn("Confirm applying BOTH (clean right and crop left)? [Y/n]: "):
                clean_right_spaces()
                crop_left_spaces()
                made_changes = True


def handle_effects_menu():
    made_changes = False
    while True:
        clear_screen()
        print("=" * WIDTH)
        print("[Effects menu]".center(WIDTH))
        print("=" * WIDTH)
        print("- G to Apply Glitch effect (random pixel corruption)")
        print("- E to Apply Earthquake effect (horizontal shakes)")
        print("- R to Apply Rain/Falling effect (vertical spill)")
        print("\nPress ESC to go back...")

        key = wait_for_key()

        if key == "\x1b":
            return made_changes
        elif key.lower() == "g":
            print()
            pct = input_number("Enter glitch effect intensity % (1-100) [N to cancel]: ")
            if pct is not None and 1 <= pct <= 100:
                if prompt_yn(f"[!] Apply Glitch effect to {pct}%? [Y/n]: "):
                    glitch_effect(pct)
                    made_changes = True
        elif key.lower() == "e":
            print()
            pct = input_number("Enter earthquake intensity % (1-100) [N to cancel]: ")
            if pct is not None and 1 <= pct <= 100:
                if prompt_yn(f"[!] Apply Earthquake effect to {pct}%? [Y/n]: "):
                    earthquake_effect(pct)
                    made_changes = True
        elif key.lower() == "r":
            print()
            pct = input_number("Enter rain intensity % (1-100) [N to cancel]: ")
            if pct is not None and 1 <= pct <= 100:
                if prompt_yn(f"[!] Apply Rain effect to {pct}%? [Y/n]: "):
                    rain_effect(pct)
                    made_changes = True


def handle_edit_menu():
    made_changes = False
    while True:
        clear_screen()
        print("=" * WIDTH)
        print("[Edit menu]".center(WIDTH))
        print("=" * WIDTH)
        print("- E to [!] CAUTION - Irreversible editing menu")
        print("\n- C to Clean spaces menu")
        print("- F to Flip Horizontal or Vertical")
        print("- I to Invert all Braille (negative color effect)")
        print("- H to Hidden Unicode texts menu")
        print("- A to Add columns or lines of Braille spaces")
        print("\nPress ESC to go back...")

        key = wait_for_key()

        if key == "\x1b":
            return made_changes
        elif key.lower() == "e":
            if handle_irreversible_menu():
                made_changes = True
        elif key.lower() == "c":
            if handle_clean_menu():
                made_changes = True
        elif key.lower() == "f":
            print()
            axis_val = input_with_esc("Flip (H)orizontal, (V)ertical? [N to cancel]: ")
            if axis_val is None:
                continue
            axis = axis_val.strip().lower()
            if axis in ["h", "v"]:
                flip_workspace(axis)
                made_changes = True
        elif key.lower() == "i":
            print()
            if prompt_yn("Confirm inverting all Braille (negative color effect)? [Y/n]: "):
                invert_all_braille()
                made_changes = True
        elif key.lower() == "h":
            if handle_hidden_menu():
                made_changes = True
        elif key.lower() == "a":
            print()
            side_val = input_with_esc("Which side to add? (T)op, (B)ottom, (L)eft, (R)ight [N to cancel]: ")
            if side_val is None:
                continue
            side_key = side_val.strip().lower()
            if side_key == "n" or side_key not in ["t", "b", "l", "r"]:
                continue

            amount = input_number("How many columns/lines to add? [N to cancel]: ")
            if amount is None or amount <= 0:
                continue

            add_padding(side_key, amount)
            made_changes = True


def handle_irreversible_menu():
    made_changes = False
    while True:
        clear_screen()
        print("=" * WIDTH)
        print("[!] CAUTION - Irreversible editing menu".center(WIDTH))
        print("=" * WIDTH)
        print("- 1 to add 1 Braille (e.g. ⠄ A3) to ALL Braille, except 'Braille Spaces'")
        print("- 2 to add 1 Braille to ALL 'Braile Space' ('⠀' U+2804, Ctrl+Shift+U)")
        print("- 3 to replace ALL selected Braille with another, except Braille spaces")
        print("\n- 4 to swap all right-dots only to left-dots with U+00A0 (NBSP)")
        print("  Note: +2 bytes for each swapped character")
        print("- 5 to revert option 4, removes NBSP and swaps left-dots back to right")
        print("\n- A to Alternates Braille spaces")
        print("- L to add 1 left-dot to the highest right-dot")
        print("- M to Mirror mode (clone and flip left->right or top->bottom)")
        print("- E to Effects menu")
        print("- D to Delete custom columns or lines (Top/Bottom/Left/Right)")
        print("\nPress ESC to go back...")

        key = wait_for_key()

        if key == "\x1b":
            return made_changes
        elif key == "1":
            print()
            val = input_with_esc(" Enter the Braille to add to ALL Braille [N to cancel]: ")
            if val is not None:
                offset = keyboard_menu(val)
                if offset is not None:
                    char_str = chr(0x2800 + offset)
                    if prompt_yn(f"[!] Add {char_str} to ALL Braille? [Y/n]: "):
                        add_custom_to_all_braille(offset)
                        made_changes = True
                else:
                    if val.strip().lower() != "n":
                        print(" [!] Invalid Braille format")
                        wait_for_key()
        elif key == "2":
            print()
            val = input_with_esc(" Enter the Braille to add to 'Braille Space' [N to cancel]: ")
            if val is not None:
                offset = keyboard_menu(val)
                if offset is not None:
                    char_str = chr(0x2800 + offset)
                    if prompt_yn(f" Confirm swapping all Braille Space to {char_str}? [Y/n]: "):
                        swap_characters("\u2800", char_str)
                        made_changes = True
                else:
                    if val.strip().lower() != "n":
                        print(" [!] Invalid Braille format")
                        wait_for_key()
        elif key == "3":
            print()
            val1 = input_with_esc(" Enter the Braille to replace [N to cancel]: ")
            if val1 is not None:
                offset1 = keyboard_menu(val1)
                if offset1 is not None:
                    val2 = input_with_esc(" Enter the replacement Braille [N to cancel]: ")
                    if val2 is not None:
                        offset2 = keyboard_menu(val2)
                        if offset2 is not None:
                            char_old = chr(0x2800 + offset1)
                            char_new = chr(0x2800 + offset2)
                            if prompt_yn(f"Confirm replacing all {char_old} with {char_new}? [Y/n]: "):
                                swap_characters(char_old, char_new)
                                made_changes = True
                        else:
                            if val2.strip().lower() != "n":
                                print(" [!] Invalid Braille format")
                                wait_for_key()
                else:
                    if val1.strip().lower() != "n":
                        print(" [!] Invalid Braille format")
                        wait_for_key()
        elif key == "4":
            print()
            if prompt_yn("Confirm swapping all right-dots only to left-handed with NBSP? [Y/n]: "):
                swap_right_to_left()
                made_changes = True
        elif key == "5":
            print()
            if prompt_yn("Confirm reverting option 4, left-dots to right-dots and remove NBSP? [Y/n]: "):
                revert_swap_right_to_left()
                made_changes = True
        elif key.lower() == "a":
            print()
            val_alt = input_with_esc(" Enter Braille to alternate with (e.g. ⠄ A3) [N to cancel]: ")
            if val_alt is not None:
                alt_offset = keyboard_menu(val_alt)
                if alt_offset is not None:
                    alt_char = chr(0x2800 + alt_offset)
                    print("\nSelect alternation mode:")
                    print("1. Perfect Grid")
                    print("2. Checkerboard")
                    mode = input_number("Choose option [1-2] [N to cancel]: ")
                    if mode in [1, 2]:
                        include_existing = prompt_yn("Include existing Braille for alternation? [Y/n]: ")
                        if include_existing is not None:
                            alternate_braille_spaces(mode, include_existing, alt_char, alt_offset)
                            made_changes = True
                else:
                    if val_alt.strip().lower() != "n":
                        print(" [!] Invalid Braille format")
                        wait_for_key()
        elif key.lower() == "l":
            print()
            if prompt_yn("[!] Add 1 left-dot in right-dots only? [Y/n]: "):
                add_left_dot_to_right_braille()
                made_changes = True
        elif key.lower() == "m":
            print()
            axis_val = input_with_esc("Mirror (C)olumns/Horizontal or (L)ines/Vertical? [N to cancel]: ")
            if axis_val is None:
                continue
            axis = axis_val.strip().lower()
            if axis == "n" or axis not in ["c", "l"]:
                continue
            amount = input_number("How many columns/lines to mirror? [N to cancel]: ")
            if amount and amount > 0:
                axis_name = "columns" if axis == "c" else "lines"
                if prompt_yn(f"[!] Apply Mirror {amount} {axis_name}? [Y/n]: "):
                    mirror_workspace(axis, amount)
                    made_changes = True
        elif key.lower() == "e":
            if handle_effects_menu():
                made_changes = True
        elif key.lower() == "d":
            print()
            target_val = input_with_esc("Which side to delete? (T)op, (B)ottom, (L)eft, (R)ight [N to cancel]: ")
            if target_val is None:
                continue
            target = target_val.strip().lower()
            side_names = {"t": "Top", "b": "Bottom", "l": "Left", "r": "Right"}

            if target in side_names:
                full_name = side_names[target]
                amount = input_number(f"How many lines/columns to delete from {full_name}? [N to cancel]: ")
                if amount is not None and amount > 0:
                    if prompt_yn(f"[!] Confirm deleting {amount} line/column(s) from {full_name}? [Y/n]: "):
                        delete_edge(target, amount)
                        made_changes = True


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":
    showing_art = False
    refresh_count = 0

    while True:
        clear_screen()

        if showing_art:
            art_lines = read_workspace_lines(strip_newlines=True)
            if art_lines is not None:
                max_cols = max((len(line) for line in art_lines), default=0)
                for idx, line in enumerate(art_lines, 1):
                    colored_line = ""
                    for char in line:
                        if "\u2800" <= char <= "\u28ff":
                            offset = ord(char) - 0x2800

                            if offset in (0x01, 0x02, 0x04, 0x40):
                                colored_line += f"\033[94m{char}\033[0m"
                            else:
                                left_dots = offset & 0x47
                                right_dots = offset & 0xB8

                                is_yellow = False
                                if bin(left_dots).count("1") == 1:
                                    if (offset & 0x01) and (offset & 0x08):
                                        is_yellow = True
                                    elif (offset & 0x02) and (offset & 0x10):
                                        is_yellow = True
                                    elif (offset & 0x04) and (offset & 0x20):
                                        is_yellow = True
                                    elif (offset & 0x40) and (offset & 0x80):
                                        is_yellow = True

                                if is_yellow:
                                    colored_line += f"\033[93m{char}\033[0m"
                                elif left_dots == 0 and right_dots > 0:
                                    colored_line += f"\033[91m{char}\033[0m"
                                else:
                                    colored_line += char
                        else:
                            colored_line += char

                    print(f"{idx:3d}║{colored_line}")

                print("   ╚" + "═" * max_cols)

                if max_cols > 0:
                    top_line = ""
                    bot_line = ""
                    third_line = ""

                    for col in range(1, max_cols + 1):
                        if col < 10:
                            top_line += str(col)
                            bot_line += " "
                            third_line += " "

                        elif col < 100:
                            top_line += str(col // 10)
                            bot_line += str(col % 10)
                            third_line += " "

                        else:
                            top_line += str(col // 100)
                            bot_line += str((col // 10) % 10)
                            third_line += str(col % 10)

                    print("    " + top_line)

                    if max_cols >= 100:
                        print("    " + bot_line)
                        print("    " + third_line)
                    elif max_cols >= 10:
                        print("    " + bot_line)

                print()
                c1 = f"   R to Refresh [{refresh_count}]"
                c_blue = "   \033[94mBlue\033[0m = 1 left-dot only"
                c_red = "   \033[91mRed\033[0m = Right-dots only"
                c_yellow = "   \033[93mYellow\033[0m = 1 left-dot on right-dot/s"

                def pad_ansi(text, width):
                    visible = re.sub(r"\033\[[0-9;]*m", "", text)
                    return text + " " * max(0, width - len(visible))

                print(pad_ansi(c1, HALF_WIDTH) + "│" + c_blue)
                print(pad_ansi(c_red, HALF_WIDTH) + "│" + c_yellow)
            else:
                print("\n [!] Workspace file not found")

            preview_key = wait_for_key()
            if preview_key.lower() == "r":
                refresh_count += 1
                continue
            else:
                showing_art = False
                continue
        else:
            logo_lines = [
                "⣿⡛⡛⣤⡀▁▄▀▀▀",
                "⣿⡶⡶⣿⡀▁▀▀▀▄",
                "⣿⣤⣤⡛⡀▁▄▄▄▀",
            ]

            title = "Braille Shades Art".center(WIDTH)
            subtitle = "ASCII Art with Braille Dots or Block Elements Shades".rjust(WIDTH - 1) + " "
            dev = "Developer: Goti Sán"
            version = "ver10.0"
            dev_centered = dev.center(WIDTH)
            line_3 = dev_centered[: -len(version) - 1] + version + " "
            empty_line = " " * WIDTH

            row1 = logo_lines[0] + title[len(logo_lines[0]) :]
            row2 = logo_lines[1] + empty_line[len(logo_lines[1]) :]
            row3 = logo_lines[2] + subtitle[len(logo_lines[2]) :]

            print(" ╔" + "═" * WIDTH + "╗")
            print(f" ║{row1}║")
            print(f" ║{row2}║")
            print(f" ║{row3}║")
            print(f" ║{line_3}║")
            print(" ╚" + "═" * WIDTH + "╝")

            file_text = f"Reading from: '{WORKSPACE_FILE}'"
            print(f"{file_text.center(WIDTH)}")
            analyze_Braille_Shades_Art_workspace()

            print("- ESC to quit")
            print(f"\n- R to Refresh [{refresh_count}]")
            print("- P to ASCII preview")
            print("- I to Information platform compatibility status")

            print("\n- E to Edit menu")
            print("- T to Text generator with aesthetic typography")
            print("- K to Keyboard menu")

            print("\n- B to Backup menu")
            print("- N to New/overwrite 'Braille_Shades_Art_workspace.txt' with 20x10 template")
            print("- M to Import or export image")

        key = wait_for_key()

        if key == "\x1b":
            print()
            break
        elif key.lower() == "r":
            refresh_count += 1
        elif key.lower() == "p":
            showing_art = not showing_art
        elif key.lower() == "i":
            show_platform_information()
        elif key.lower() == "e":
            if handle_edit_menu():
                refresh_count += 1
        elif key.lower() == "t":
            handle_text_generator_menu()
        elif key.lower() == "k":
            handle_keyboard_menu()
        elif key.lower() == "b":
            if handle_backup_menu():
                refresh_count += 1
        elif key.lower() == "n":
            print()
            if prompt_yn("[!] CAUTION: Overwrite 'Braille_Shades_Art_workspace.txt', proceed? [Y/n]: "):
                if prompt_yn("[!] Any existing art will be permanently lost! [Y/n]: "):
                    generate_blank_workspace()
                    refresh_count += 1
        elif key.lower() == "m":
            if handle_image_menu():
                refresh_count += 1
