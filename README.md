![Lint](https://github.com/HSE-JetBrains-department/2023_similar_dev_search_akhundov/actions/workflows/lint.yml/badge.svg)  
![Test](https://github.com/HSE-JetBrains-department/2023_similar_dev_search_akhundov/actions/workflows/test.yml/badge.svg)

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
python -m simdev <аргументы_cli>
```

### Docker

- Собрать image

```
docker build -t theseems/simdev:latest .
```

- Запуск:

```shell
docker run -it --rm --name theseems_simdev -v ${pwd}/simdev/cache:/app/cache -v ${pwd}/simdev/results:/app/results theseems/simdev:latest <аргументы_cli>
```

Таким образом (`-v ...`) мы передаем закешированные данные из папки `cache` корня
проекта в окружение контейнера, откуда с ними может проводиться работа.
Результаты также прокидываются в контейнер (и из него) из папки `results`

## CLI

<аргументы_cli>

### Популярные репозитории

`top`: `top --source TheSeems/TMoney --processes 5 --count 5` (вычислить топ-5
популярных репозиториев среди поставивших звезду репозиторию TheSeems/TMoney, сбор
информации о поставивших звезду проводится в 5 процессов)

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

`clone`: `clone --source https://github.com/TheSeems/TMoney --source https://github.com/TheSeems/HseNotebooks --limit 50 --export results/dev_info.json` (
склонировать репозитории TheSeems/TMoney, TheSeems/HseNotebooks, обработать 50 коммитов
из каждого,
сохранить информацию о коммитерах и об их файлах в `results/dev_info.json`)

`clone`: `clone --load results/popular_repos.json --limit 50 --export` (склонировать
репозитории
из `results/popular_repos.json`, обработать 50 коммитов из каждого, сохранить информацию
о коммитерах и об их файлах
в `results/dev_info.json`)

```text
Options:
  --source TEXT    List of repositories to fetch information about
  --limit INTEGER  Max amount of commits to process
  --load FILE      Path to popular repositories to load repositories from.
                   Overrides --source option
  --export FILE    Path to store results to
```

### Поиск схожих разработчиков

`search`: `search 
--source me@theseems.ru
--info results/dev_info.json
--limit 10
--top_size 3
--export results/similar/me@theseems.ru.json`
(Поиск <=10 похожих разработчиков, похожих на me@theseems.ru среди результатов,
подсчитанных ранее и
сохраненных в results/dev_info.json с сохранением оценок и парамтров (топ-3 языков,
идентификаторов, репозиториев) в
results/similar/me@theseems.ru.json)

```text
  --source TEXT       Email of the developer to find similar developers to
                      [required]
  --info FILE         Path to dev info file (computer during `clone` command)
                      [required]
  --export FILE       Path to store results to
  --limit INTEGER     How many developers to search for at most (with highest
                      similarity score)
  --top_size INTEGER  Top-n meta params (languages, identifiers, repositories)
  --help              Show this message and exit.
```

## Автор

Студент 3 курса, Ахундов Алексей Назимович, БПИ202