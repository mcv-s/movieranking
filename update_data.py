import json
import os
import sys
from pathlib import Path

import requests


# ============================================================
# CONFIG
# ============================================================

MOVIES_FILE = Path("movies_list.txt")
DATA_FILE = Path("movies_data.json")

API_KEY = os.environ.get("API_KEY")

SEARCH_URL = "https://api.watchmode.com/v1/search/"
DETAIL_URL = "https://api.watchmode.com/v1/title/{title_id}/details/"


# ============================================================
# VALIDATE API KEY
# ============================================================

if not API_KEY:
    print("ERROR: API_KEY environment variable is not set.")
    sys.exit(1)


# ============================================================
# READ MOVIE LIST
# ============================================================

if not MOVIES_FILE.exists():
    print(f"ERROR: {MOVIES_FILE} does not exist.")
    sys.exit(1)


with MOVIES_FILE.open("r", encoding="utf-8") as file:
    movies = [
        line.strip()
        for line in file
        if line.strip()
    ]


print(f"Found {len(movies)} movies in {MOVIES_FILE}")


# ============================================================
# READ EXISTING JSON
# ============================================================

if DATA_FILE.exists():
    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            movie_data = json.load(file)

        if not isinstance(movie_data, dict):
            print("ERROR: movies_data.json must contain a JSON object.")
            sys.exit(1)

    except json.JSONDecodeError:
        print("ERROR: movies_data.json contains invalid JSON.")
        sys.exit(1)

else:
    print("movies_data.json does not exist. Creating a new one.")
    movie_data = {}


# ============================================================
# FIND NEW MOVIES
# ============================================================

# Match movie names case-insensitively.
existing_movies = {
    title.lower()
    for title in movie_data.keys()
}

new_movies = [
    movie
    for movie in movies
    if movie.lower() not in existing_movies
]


print(f"Movies already in JSON: {len(movie_data)}")
print(f"New movies to look up: {len(new_movies)}")


if not new_movies:
    print("No new movies found. Nothing to update.")
    sys.exit(0)


# ============================================================
# WATCHMODE API FUNCTIONS
# ============================================================

def search_movie(movie_name):
    """Search Watchmode for a movie and return the first result."""

    params = {
        "apiKey": API_KEY,
        "search_field": "name",
        "search_value": movie_name,
        "types": "movie",
    }

    response = requests.get(
        SEARCH_URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    results = data.get("title_results", [])

    if not results:
        return None

    return results[0]


def get_movie_details(title_id):
    """Get detailed information about a Watchmode title."""

    url = DETAIL_URL.format(title_id=title_id)

    params = {
        "apiKey": API_KEY,
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def clean_image_url(url):
    """Remove query parameters from image URLs."""

    if not url:
        return None

    return url.split("?")[0]


# ============================================================
# FETCH NEW MOVIE DATA
# ============================================================

for index, movie_name in enumerate(new_movies, start=1):

    print(
        f"[{index}/{len(new_movies)}] "
        f"Looking up: {movie_name}"
    )

    try:

        # ----------------------------------------------------
        # SEARCH
        # ----------------------------------------------------

        search_result = search_movie(movie_name)

        if not search_result:
            print(f"  WARNING: Could not find '{movie_name}'")
            continue

        title_id = search_result.get("id")

        if not title_id:
            print(f"  WARNING: No title ID for '{movie_name}'")
            continue


        # ----------------------------------------------------
        # DETAILS
        # ----------------------------------------------------

        details = get_movie_details(title_id)


        # ----------------------------------------------------
        # EXTRACT DATA
        # ----------------------------------------------------

        description = details.get("plot_overview")

        poster = clean_image_url(
            details.get("posterLarge")
            or details.get("poster")
        )

        release_date = (
            details.get("release_date")
            or details.get("year")
        )

        # Watchmode provides genre names as a list.
        # Use an empty list if no genres are available.
        genres = details.get("genre_names") or []


        # ----------------------------------------------------
        # SAVE MOVIE
        # ----------------------------------------------------

        movie_data[movie_name] = {
            "description": description,
            "poster": poster,
            "release_date": release_date,
            "genres": genres,
        }


        print("  Added successfully.")


    except requests.RequestException as error:

        print(
            f"  ERROR: API request failed for "
            f"'{movie_name}': {error}"
        )

    except Exception as error:

        print(
            f"  ERROR processing "
            f"'{movie_name}': {error}"
        )


# ============================================================
# WRITE UPDATED JSON
# ============================================================

with DATA_FILE.open("w", encoding="utf-8") as file:

    json.dump(
        movie_data,
        file,
        indent=2,
        ensure_ascii=False
    )

    file.write("\n")


print()
print("Done!")
print(f"Total movies in JSON: {len(movie_data)}")
print(f"Saved to: {DATA_FILE}")

