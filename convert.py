import os
from tkinter import Tk, Label, Button, filedialog, messagebox

def convert_text_to_txt_in_folder(directory):
    """
    Chuyển đổi tất cả các file .text trong thư mục và các thư mục con thành .txt.

    Args:
        directory (str): Đường dẫn đến thư mục cần xử lý.
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".text"):
                old_path = os.path.join(root, file)
                new_path = os.path.join(root, file.replace(".text", ".txt"))
                
                # Đổi tên file từ .text sang .txt
                os.rename(old_path, new_path)
                print(f"Đã chuyển: {old_path} -> {new_path}")

def select_folder():
    """
    Mở hộp thoại chọn thư mục và xử lý chuyển đổi file.
    """
    folder_path = filedialog.askdirectory(title="Chọn thư mục cần chuyển đổi")
    if folder_path:
        confirm = messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn chuyển đổi các file .text trong thư mục:\n{folder_path}?")
        if confirm:
            convert_text_to_txt_in_folder(folder_path)
            messagebox.showinfo("Hoàn tất", "Tất cả các file .text đã được chuyển đổi thành .txt!")
        else:
            messagebox.showinfo("Hủy bỏ", "Quá trình chuyển đổi đã bị hủy.")
    else:
        messagebox.showwarning("Chưa chọn thư mục", "Vui lòng chọn một thư mục để tiếp tục.")

def create_gui():
    """
    Tạo giao diện người dùng GUI để chọn thư mục và chuyển đổi file.
    """
    root = Tk()
    root.title("Chuyển đổi file .text thành .txt")
    root.geometry("400x200")
    root.resizable(False, False)

    # Nhãn thông báo
    label = Label(root, text="Chọn thư mục chứa các file .text để chuyển thành .txt", wraplength=350, pady=20)
    label.pack()

    # Nút chọn thư mục
    button_select = Button(root, text="Chọn Thư Mục", command=select_folder, padx=10, pady=5)
    button_select.pack(pady=10)

    # Thoát chương trình
    button_exit = Button(root, text="Thoát", command=root.quit, padx=10, pady=5)
    button_exit.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    create_gui()
