<p align="center">
  <img src='../images/logo.png' width=550>
</p>

<p align="center">
    【<a href="../doc/README-English.md">英语</a> | 中文 | <a href="../doc/README-Japanese.md">日语</a>】
</p>

## 📖 概览

<p align="center">
  <img src='../images/example.jpg' width=600>
</p>

## ❓ PDF比较器能做什么？

1. 图片差异对比

<p align="center">
  <img src='../images/example_image.jpg' width=600>
</p>

2. 文本差异对比

<p align="center">
  <img src='../images/example_text.jpg' width=600>
</p>

### 🖥️ 快速启动

请按照以下步骤操作：

1. **克隆GitHub存储库：** 使用以下命令克隆存储库：

```bash
git clone https://github.com/VintLin/pdf-comparator.git
```

1. **设置Python环境：** 打开“pdf-comparator”项目目录，确保您具有3.8或更高版本的Python环境。您可以使用以下命令创建并激活此环境，将“venv”替换为您喜欢的环境名称：

```bash
cd pdf-comparator
python3 -m venv venv
```

2. **安装依赖项：** 通过运行以下命令安装所需的依赖项：

```bash
pip3 install -r requirements.txt
```

3. **直接运行代码：** 通过运行以下命令对比PDF文件：

```bash
python3 -m pdfcomparator "/compare_file_1.pdf" "/compare_file_2.pdf" "/result_folder/" --image --text
```

4. **构建可执行文件：** 你也可以根据需要通过cx-Freeze构建可执行文件 (执行成功后可以在“/build/”找到可执行文件)：

```bash
python3 setup.py build
```

5. **运行可执行文件：** 通过运行以下命令比对PDF文件：

```bash
../pdfcomparator.exe "/compare_file_1.pdf" "/compare_file_2.pdf" "/result_folder/" --image --text
```

### 命令行参数使用说明

这个程序接受以下命令行参数：

- `file1` (必需)：输入文件1的路径。请提供您要比较的第一个文件的路径。

- `file2` (必需)：输入文件2的路径。请提供您要比较的第二个文件的路径。

- `output_folder` (必需)：输出文件夹的路径。比较结果将会被保存在这个文件夹中。

- `--image`：可选参数，如果指定该选项，程序将会执行图像比较。默认情况下启用此选项。

- `--text`：可选参数，如果指定该选项，程序将会执行文本比较。默认情况下禁用此选项。

- `--cache` 或 `-c`：可选参数，用于指定缓存路径。如果指定了缓存路径，程序将会使用缓存来加速比较过程。默认情况下不启用缓存。

### 例子

以下是一些使用示例：

```bash
# 执行图像比较
python3 -m pdfcomparator file1.pdf file2.pdf output_folder/ --image

# 执行文本比较
python3 -m pdfcomparator file1.pdf file2.pdf output_folder/ --text

# 执行图像比较，并启用缓存
python3 -m pdfcomparator file1.pdf file2.pdf output_folder/ --image --cache /path/to/cache
```

## 👨‍💻‍ 贡献者

<a href="https://github.com/VintLin/pdf-comparator/contributors">
  <img src="https://contrib.rocks/image?repo=VintLin/pdf-comparator" />
</a>

使用[contrib.rocks](https://contrib.rocks)制作。

## ⚖️ 许可证

- 源代码许可证：我们的项目源代码根据MIT许可证授权。该许可证允许使用、修改和分发代码，但受到MIT许可证中概述的某些条件的限制。
- 项目开源状态：该项目确实是开源的，但主要用于非商业目的。虽然我们鼓励社区合作和贡献，用于商业目的的项目组件的任何使用都需要单独的许可协议。

## 🌟 星标历史

[![星标历史图表](https://api.star-history.com/svg?repos=VintLin/pdf-comparator&type=Date)](https://star-history.com/#VintLin/pdf-comparator&Date)

## 📬 联系

如果您有任何问题、反馈或想与我们联系，请随时通过电子邮件[vintonlin@gmail.com](mailto:vintonlin@gmail.com)与我们联系。