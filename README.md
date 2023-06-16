![Lint and test](https://github.com/HSE-JetBrains-department/2023_similar_dev_search_akhundov/actions/workflows/lint_and_test.yml/badge.svg)

---

# Поиск схожих разработчиков

Проект по дисциплине "Исходный код как данные" 3 курса ПИ ФКН НИУ ВШЭ.

## Pipeline

1. Поиск репозиториев для анализа
2. Клонирование найденных репозиториев
3. Извлечение информации с использованием системы контроля версий
4. Классификация файлов репозитория по языку программирования
5. Фильтрация содержимого
6. Парсинг содержимого в соответствии с ЯП: извлечение информации об импортах, именах
   переменных из дерева абстрактного синтаксиса
7. Поиск схожих разработчиков: каждому разработчику сопоставляется 2 вектора: с
   информацией о используемых языках и с информацией о содежимом кода

## Сборка

В предположении, что содержимое репозитория находится в текущей рабочей директории

### Вручную

- Настройка окружения

```shell
python3 -m venv venv
pip install -r requirements.txt
```

- Запуск:

```shell
python simdev/main.py <аргументы_cli>
```

### Docker

- Собрать image

```
docker build -t theseems/simdev:latest .
```

- Запуск:

```shell
docker run -it --name theseems_simdev -v cache:/app/cache -v results:/app/results theseems/simdev:latest 
python simdev/main.py <аргументы_cli>
```

Таким образом (`-v ...`) мы передаем закешированные данные из папки `cache` корня
проекта в окружение контейнера, откуда с ними может проводиться работа.
Результаты также прокидываются в контейнер (и из него) из папки `results`

## CLI
<аргументы_cli>

### Популярные репозитории
`top`: `top --source TheSeems/TMoney --processes 5 --count 5` (вычислить топ-5 популярных репозиториев среди поставивших звезду репозиторию TheSeems/TMoney, сбор информации о поставивших звезду проводится в 5 процессов)
```text
  --source TEXT         List of initial repositories to get top starred by
                        stargazers of
  --tokens TEXT         List of GitHub API tokens to fetch information with
  --processes INTEGER   Number of processes to fetch starred repositories in
  --count INTEGER       Max amount of top popular repositories to get
  --page_limit INTEGER  GitHub API page limit
  --help                Show this message and exit.
```

### Клонирование репозиториев
`clone`: `clone --source https://github.com/TheSeems/TMoney --source https://github.com/TheSeems/HseNotebooks` (склонировать репозитории TheSeems/TMoney, TheSeems/HseNotebooks, выдать информацию о коммитерах и об их файлах)
```text
Options:
  --source TEXT  List of repositories to fetch information about
```

### Поиск схожих разработчиков
TBD...

## Автор

Студент 3 курса, Ахундов Алексей Назимович, БПИ202