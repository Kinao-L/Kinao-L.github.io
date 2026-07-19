# Leaflet cluster map of talk locations
#
# Run this script from the root directory of the GitHub Pages project.
# It reads location information from Markdown files in _talks/,
# geocodes each location with geopy/Nominatim, and generates
# a standalone Leaflet cluster map using getorg.

import glob
import time

import frontmatter
import getorg
from geopy import Nominatim
from geopy.exc import GeocoderServiceError, GeocoderTimedOut

# Geocoding timeout in seconds
TIMEOUT = 10

# Pause between requests to avoid sending requests too quickly to Nominatim
REQUEST_INTERVAL = 1

# Collect Markdown files
markdown_files = glob.glob("_talks/*.md")

# Prepare geocoder
geocoder = Nominatim(user_agent="Kinao-L.github.io-talkmap")

# getorg expects:
# {
#     "description": geopy_location_object
# }
location_dict = {}


def normalize_locations(data):
    """
    Convert location or locations fields into a unified list.

    Supported formats:

    location: "Kyoto, Japan"

    location:
      - "Kyoto, Japan"
      - "Tokyo, Japan"

    locations:
      - "Kyoto, Japan"
      - "Tokyo, Japan"

    locations:
      - city: Kyoto
        country: Japan
      - city: Tokyo
        country: Japan
    """

    raw_locations = data.get("locations", data.get("location"))

    if raw_locations is None:
        return []

    # Single string
    if isinstance(raw_locations, str):
        location = raw_locations.strip()
        return [location] if location else []

    # Multiple locations
    if isinstance(raw_locations, list):
        normalized = []

        for item in raw_locations:
            # Example:
            # - "Kyoto, Japan"
            if isinstance(item, str):
                location = item.strip()

                if location:
                    normalized.append(location)

            # Example:
            # - city: Kyoto
            #   country: Japan
            elif isinstance(item, dict):
                city = str(item.get("city", "")).strip()
                country = str(item.get("country", "")).strip()

                location_parts = [
                    part for part in [city, country] if part
                ]

                if location_parts:
                    normalized.append(", ".join(location_parts))

        return normalized

    print(f"Unsupported location format: {raw_locations}")
    return []


# Perform geolocation
for file_path in markdown_files:
    try:
        post = frontmatter.load(file_path)
        data = post.to_dict()
    except Exception as ex:
        print(f"Error reading {file_path}: {ex}")
        continue

    title = str(data.get("title", "Untitled Talk")).strip()
    venue = str(data.get("venue", "")).strip()
    talk_type = str(data.get("type", "")).strip()
    date = str(data.get("date", "")).strip()
    permalink = str(data.get("permalink", "")).strip()

    locations = normalize_locations(data)

    if not locations:
        print(f"Skipped {file_path}: no valid location found.")
        continue

    for location in locations:
        description_parts = [title]

        if talk_type:
            description_parts.append(talk_type)

        if venue:
            description_parts.append(venue)

        if date:
            description_parts.append(date)

        description_parts.append(location)

        # Make title clickable when permalink exists
        if permalink:
            description = (
                f'<a href="{permalink}">{title}</a><br />'
                + "<br />".join(description_parts[1:])
            )
        else:
            description = "<br />".join(description_parts)

        try:
            geocoded_location = geocoder.geocode(
                location,
                timeout=TIMEOUT
            )

            if geocoded_location is None:
                print(f"Location not found: {location}")
                continue

            # Prevent duplicated dictionary keys
            unique_description = description
            duplicate_number = 2

            while unique_description in location_dict:
                unique_description = (
                    f"{description}<br />Entry {duplicate_number}"
                )
                duplicate_number += 1

            location_dict[unique_description] = geocoded_location

            print(
                f"Found: {location} -> "
                f"{geocoded_location.latitude}, "
                f"{geocoded_location.longitude}"
            )

            time.sleep(REQUEST_INTERVAL)

        except GeocoderTimedOut as ex:
            print(f"Geocoding timed out for {location}: {ex}")

        except GeocoderServiceError as ex:
            print(f"Geocoding service error for {location}: {ex}")

        except ValueError as ex:
            print(f"Invalid geocoding input {location}: {ex}")

        except Exception as ex:
            print(
                f"Unexpected error while processing {location}: {ex}"
            )


# Generate map only when at least one location was found
if not location_dict:
    print("No locations were successfully geocoded. Map was not generated.")
else:
    getorg.orgmap.create_map_obj()

    getorg.orgmap.output_html_cluster_map(
        location_dict,
        folder_name="talkmap",
        hashed_usernames=False
    )

    print(
        f"Talk map generated successfully with "
        f"{len(location_dict)} location(s)."
    )