# Multi-Frame and Multi-Camera Batch Render Add-on

## English

### Overview

This Blender add-on lets you create a per-scene list of camera entries and render specified frames or ranges per camera in a single batch operation. The add-on switches the active camera for each job and renders frames sequentially using a modal operator so the UI remains responsive.

### Key features

- Per-scene camera entries with: camera object, "Frames / Ranges" string, and "Show Preview" toggle.
- Add/remove entries manually or use "Add All Cameras" (natural sort by name).
- Fill empty frame fields from a single scene-wide string using "Fill Empty Frame Fields".
- Batch render via a modal operator that processes one camera job at a time.
- Skip existing files when overwrite is disabled (supported formats: PNG, JPEG, BMP, TIFF, OPEN_EXR).
- Output files are saved as <camera_name>_frame<frame> with the format extension.

### Frame / Range syntax

- Single frames: `1` -> frame 1
- Multiple frames: `1,5,10` -> frames 1, 5, 10
- Ranges: `10-12` -> frames 10, 11, 12
- Mixed: `1,3-5,8` -> frames 1, 3, 4, 5, 8

Rules:

- Tokens are comma-separated; whitespace is ignored.
- Range tokens use `start-end` (inclusive). Invalid tokens raise an error and the field will not be accepted.

### How to use

1. Open the Render Properties tab and find the "Frame & Camera Selector" panel.
2. Add camera entries or click "Add All Cameras" to populate the list.
3. For each camera entry, choose a camera, enter the `Frames / Ranges` string, and set `Show Preview` if you want the interactive render window.
4. Optionally set a scene-wide `Fill Frames / Ranges` string and click "Fill Empty Frame Fields" to populate empty entries.
5. Make sure the Render Output path (`Output Properties > Output > Path`) points to a directory, not a single file.
6. Click the green "Render Frames" button to start the batch process.

### Notes

- The operator uses `INVOKE_DEFAULT` when `Show Preview` is enabled (shows Blender's render window) and `EXEC_DEFAULT` when disabled (no preview). Disabling preview may block Blender's UI for each render call.
- Files are saved in the configured output folder using the camera name and frame number. If `Overwrite` is disabled and a supported-format file exists, that frame is skipped.
- Ensure the Render Output is a folder (not a specific file). The add-on checks that the output path resolves to an existing directory.
- Supported automatic extension mapping: PNG -> .png, JPEG -> .jpg, BMP -> .bmp, TIFF -> .tiff, OPEN_EXR -> .exr.

### Installation

1. Download the repository as ZIP or copy the addon folder into Blender's `addons` folder.
2. In Blender, go to `Edit > Preferences > Add-ons` and install/enable the add-on.

### Tested

- Registered `bl_info` targets Blender 2.80+, tested with Blender 4.1.0.

### Troubleshooting

- If frame parsing fails, check the `Frames / Ranges` string for invalid tokens.
- If output files are not created, verify the Render Output path is a valid directory and that you have write permissions.
- If preview rendering fails on your system, try disabling `Show Preview` for entries.

---

## Русский

### Обзор

Этот аддон для Blender позволяет хранить в сцене список камер с указанными кадрами/диапазонами и запускать пакетную отрисовку по одной камере за раз. Активная камера переключается автоматически, а рендер выполняется в модальном операторе, чтобы интерфейс оставался отзывчивым.

### Основные возможности

- Записи по сцене: объект камеры, поле "Frames / Ranges" и переключатель "Show Preview".
- Добавление/удаление записей вручную или кнопкой "Add All Cameras" (натуральная сортировка по имени).
- Заполнение пустых полей кадров общей строкой сцены через "Fill Empty Frame Fields".
- Пакетный рендер реализован в модальном операторе, который выполняет задания по одной камере.
- Пропуск существующих файлов при отключённой перезаписи (поддерживаемые форматы: PNG, JPEG, BMP, TIFF, OPEN_EXR).
- Файлы сохраняются как <camera_name>_frame<frame>.<ext> в папке Render Output.

### Синтаксис кадров и диапазонов

- Один кадр: `1` -> кадр 1
- Несколько кадров: `1,5,10` -> кадры 1, 5, 10
- Диапазон: `10-12` -> кадры 10, 11, 12
- Смешанный: `1,3-5,8` -> кадры 1, 3, 4, 5, 8

Правила:

- Токены разделяются запятыми; пробелы игнорируются.
- Диапазоны задаются `start-end` (включительно). Неправильный токен вызовет ошибку.

### Как пользоваться

1. Откройте вкладку Render Properties и найдите панель "Frame & Camera Selector".
2. Добавьте записи камер или нажмите "Add All Cameras".
3. Для каждой записи выберите камеру, введите строку `Frames / Ranges` и включите `Show Preview`, если нужна интерактивная отрисовка.
4. При необходимости задайте общую строку `Fill Frames / Ranges` в сцене и нажмите "Fill Empty Frame Fields".
5. Убедитесь, что путь для вывода (`Output Properties > Output > Path`) указывает на папку, а не на единичный файл.
6. Нажмите зелёную кнопку "Render Frames", чтобы запустить пакетный рендер.

### Примечания

- Оператор использует `INVOKE_DEFAULT`, если включён `Show Preview` (показывает окно рендера), и `EXEC_DEFAULT`, если выключен. При отключённом превью Blender может блокироваться во время рендера кадра.
- Файлы сохраняются в указанную папку с именем камеры и номером кадра. Если перезапись отключена и файл в поддерживаемом формате существует, кадр будет пропущен.
- Убедитесь, что Output Path — это папка; аддон проверяет, что путь является директорией.
- Соответствие форматов: PNG -> .png, JPEG -> .jpg, BMP -> .bmp, TIFF -> .tiff, OPEN_EXR -> .exr.

### Установка

1. Скачайте репозиторий ZIP или поместите папку аддона в директорию `addons` Blender.
2. В Blender откройте `Edit > Preferences > Add-ons` и установите/включите аддон.

### Совместимость

- `bl_info` нацелен на Blender 2.80+, проверялось на Blender 4.1.0.

### Устранение неполадок

- Если разбор строк кадров не проходит — проверьте синтаксис в `Frames / Ranges`.
- Если файлы не создаются — проверьте путь вывода и права на запись.
- При проблемах с превью попробуйте отключить `Show Preview` для записей.

---

## License / Лицензия

See project repository for license details.
