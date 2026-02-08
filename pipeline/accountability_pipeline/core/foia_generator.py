"""FOIA request generation and tracking.

Generates formal FOIA letters for ICE agencies using Jinja2 templates
and creates CSV trackers for request management.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from jinja2 import Template

from accountability_pipeline.models.schemas import FOIARequest
from accountability_pipeline.utils.file_handler import write_csv, write_text, ensure_directory
from accountability_pipeline.utils.logger import get_logger

logger = get_logger(__name__)

# Default FOIA letter template
FOIA_LETTER_TEMPLATE = """\
{{ requester_name }}
{{ requester_address }}
{{ requester_email }}

{{ date }}

FOIA Officer
{{ agency_name }}
{{ agency_address }}

Re: Freedom of Information Act Request

Dear FOIA Officer:

Pursuant to the Freedom of Information Act (FOIA), 5 U.S.C. § 552, I am requesting access to and copies of the following records:

{{ description }}

{% if date_range_start and date_range_end -%}
The time period for this request is from {{ date_range_start }} to {{ date_range_end }}.
{% endif -%}

I am requesting this information as {{ requester_role }}.

I am willing to pay reasonable duplication fees for the processing of this request in an amount not to exceed ${{ fee_limit }}. Please notify me prior to your incurring any expenses in excess of that amount.

If my request is denied in whole or in part, I ask that you justify all deletions by reference to specific exemptions of the Act.

I expect a response within 20 business days, as provided by law.

Thank you for your consideration of this request.

Sincerely,

{{ requester_name }}
"""

# Default agency addresses
DEFAULT_AGENCIES: Dict[str, Dict[str, str]] = {
    "ICE": {
        "name": "U.S. Immigration and Customs Enforcement",
        "address": "Freedom of Information Act Office\n500 12th Street, SW, Stop 5009\nWashington, DC 20536-5009",
    },
    "CBP": {
        "name": "U.S. Customs and Border Protection",
        "address": "FOIA Division\n90 K Street, NE, 9th Floor\nWashington, DC 20229",
    },
    "DHS": {
        "name": "Department of Homeland Security",
        "address": "Privacy Office, Mail Stop 0655\nDepartment of Homeland Security\n2707 Martin Luther King Jr. Ave. SE\nWashington, DC 20528-0655",
    },
    "DOJ": {
        "name": "Department of Justice",
        "address": "Office of Information Policy\nSuite 11050\n1425 New York Avenue, NW\nWashington, DC 20530-0001",
    },
}

# Default requester info (to be overridden by config)
DEFAULT_REQUESTER = {
    "name": "[Your Name]",
    "address": "[Your Address]",
    "email": "[Your Email]",
    "role": "a member of the public seeking information in the public interest",
    "fee_limit": "25.00",
}


def generate_foia_requests(
    agencies: List[str],
    output_dir: str,
    subject: str = "ICE enforcement actions and personnel records",
    description: str = "",
    date_range_start: Optional[date] = None,
    date_range_end: Optional[date] = None,
    requester_info: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Generate formal FOIA request letters for specified agencies.

    Args:
        agencies: List of agency codes (e.g., ['ICE', 'CBP']).
        output_dir: Directory to write generated letters.
        subject: Subject line for the FOIA request.
        description: Detailed description of records requested.
        date_range_start: Start of time period for records.
        date_range_end: End of time period for records.
        requester_info: Requester details override.

    Returns:
        Dict mapping agency code to output file path.
    """
    ensure_directory(output_dir)
    requester = {**DEFAULT_REQUESTER, **(requester_info or {})}

    if not description:
        description = (
            "All records related to enforcement actions, personnel complaints, "
            "use of force incidents, and internal investigations involving ICE agents "
            "and officers, including but not limited to: incident reports, complaint files, "
            "disciplinary records, and internal affairs investigation files."
        )

    template = Template(FOIA_LETTER_TEMPLATE)
    results: Dict[str, str] = {}

    for agency_code in agencies:
        agency_code_upper = agency_code.upper()
        agency = DEFAULT_AGENCIES.get(agency_code_upper)
        if agency is None:
            agency = {
                "name": agency_code,
                "address": "[Agency Address Required]",
            }
            logger.warning("unknown_agency", agency=agency_code)

        letter_content = template.render(
            requester_name=requester["name"],
            requester_address=requester["address"],
            requester_email=requester["email"],
            date=datetime.now().strftime("%B %d, %Y"),
            agency_name=agency["name"],
            agency_address=agency["address"],
            description=description,
            date_range_start=date_range_start.isoformat() if date_range_start else None,
            date_range_end=date_range_end.isoformat() if date_range_end else None,
            requester_role=requester["role"],
            fee_limit=requester["fee_limit"],
        )

        filename = f"foia_request_{agency_code_upper}_{date.today().isoformat()}.txt"
        file_path = os.path.join(output_dir, filename)
        write_text(letter_content, file_path)

        results[agency_code_upper] = file_path
        logger.info("foia_generated", agency=agency_code_upper, path=file_path)

    return results


def create_foia_tracker_csv(output_path: str) -> str:
    """Create a template CSV for tracking FOIA request status.

    The tracker includes columns for request management, response tracking,
    and document cataloging.

    Args:
        output_path: Path for the output CSV file.

    Returns:
        The output file path.
    """
    fieldnames = [
        "request_id",
        "agency",
        "date_submitted",
        "subject",
        "tracking_number",
        "status",
        "response_date",
        "documents_received",
        "pages_received",
        "exemptions_cited",
        "appeal_filed",
        "appeal_date",
        "notes",
    ]

    example_row = {
        "request_id": "FOIA-001",
        "agency": "ICE",
        "date_submitted": date.today().isoformat(),
        "subject": "Example: Enforcement actions 2024-2025",
        "tracking_number": "",
        "status": "Submitted",
        "response_date": "",
        "documents_received": "0",
        "pages_received": "0",
        "exemptions_cited": "",
        "appeal_filed": "No",
        "appeal_date": "",
        "notes": "Template row - replace with actual data",
    }

    write_csv([example_row], output_path, fieldnames=fieldnames)
    logger.info("tracker_created", path=output_path)
    return output_path


def create_foia_request_objects(
    agencies: List[str],
    subject: str,
    description: str,
    date_range_start: Optional[date] = None,
    date_range_end: Optional[date] = None,
) -> List[FOIARequest]:
    """Create FOIARequest model objects without writing files.

    Useful for programmatic tracking and state management.

    Args:
        agencies: List of agency codes.
        subject: Request subject.
        description: Detailed description.
        date_range_start: Optional start date.
        date_range_end: Optional end date.

    Returns:
        List of FOIARequest model instances.
    """
    requests = []
    for agency_code in agencies:
        req = FOIARequest(
            agency=agency_code.upper(),
            subject=subject,
            description=description,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
        )
        requests.append(req)

    return requests
