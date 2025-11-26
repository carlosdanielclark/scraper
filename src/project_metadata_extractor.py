# src/metadata_extractor.py

from typing import Any, Dict, Optional

from playwright.sync_api import Page

from src.utils.logger import get_logger

logger = get_logger("metadata")


class BuildingConnectedMetaBuildingConnectedBidBoardScraper:
    """
    Extrae metadatos de la página de un proyecto en BuildingConnected.

    Devuelve un dict con la forma:

      {
        "client": { "name": ..., "email": ..., "phone": ... },
        "date_due": ...,
        "project_name": ...,
        "location": ...,
        "project_size": ...,
        "project_information": ...
      }
    """

    def __init__(self, page: Page) -> None:
        self.page = page

    # ------------------------- MÉTODO PÚBLICO ------------------------- #

    def extract(self) -> Dict[str, Any]:
        """Extrae todos los metadatos relevantes de la página de proyecto."""
        client = self._extract_client()
        date_due = self._extract_date_due()
        project_name = self._extract_value_by_header("Project Name")
        location = self._extract_value_by_header("Location")
        project_size = self._extract_value_by_header("Project Size")
        project_info = self._extract_project_information()

        logger.info("[📋] Metadatos extraídos (Fase 3 - metadatos):")
        logger.info(f"      Client.Name:  {client.get('name')}")
        logger.info(f"      Client.Email: {client.get('email')}")
        logger.info(f"      Client.Phone: {client.get('phone')}")
        logger.info(f"      Date Due:     {date_due}")
        logger.info(f"      Project Name: {project_name}")
        logger.info(f"      Location:     {location}")
        logger.info(f"      Project Size: {project_size}")
        logger.info(f"      Info Len:     {len(project_info) if project_info else 0}")

        return {
            "client": client,
            "date_due": date_due,
            "project_name": project_name,
            "location": location,
            "project_size": project_size,
            "project_information": project_info,
        }

    # ---------------------- CLIENT (NAME/EMAIL/PHONE) ---------------------- #

    def _extract_client(self) -> Dict[str, Optional[str]]:
        """
        Extrae Client.Name, Client.Email y Client.Phone usando:
        - companyDetails → nombre del cliente
        - leadDetailsText / leadContactInfo → teléfono y correo
        """
        name: Optional[str] = None
        email: Optional[str] = None
        phone: Optional[str] = None

        try:
            company_locator = self.page.locator(
                "xpath=//div[contains(@class,'companyDetails')]"
                "/descendant::div[contains(@class,'textWrapper')][1]"
            )
            if company_locator.count() > 0:
                raw_name = company_locator.first.text_content() or ""
                name = raw_name.strip() or None

            lead_text_locator = self.page.locator(
                "xpath=//div[contains(@class,'leadDetailsText')]"
            ).first

            if lead_text_locator.count() > 0:
                contact_spans = lead_text_locator.locator(
                    "xpath=.//span[contains(@class,'leadContactInfo')]"
                )
                count = contact_spans.count()

                for i in range(count):
                    span = contact_spans.nth(i)
                    raw = (span.text_content() or "").strip()

                    if not raw:
                        inner_text = span.locator(
                            "xpath=.//div[contains(@class,'textWrapper')]"
                        ).first
                        if inner_text.count() > 0:
                            raw = (inner_text.text_content() or "").strip()

                    if not raw:
                        continue

                    if "@" in raw:
                        email = raw
                    elif any(ch.isdigit() for ch in raw):
                        phone = raw

        except Exception as e:
            logger.warning(f"[⚠️] Error extrayendo metadatos de Client: {e}")

        return {
            "name": name,
            "email": email,
            "phone": phone,
        }

    # ---------------------- CAMPOS POR HEADER (XPATH) ---------------------- #

    def _locate_header(self, header_text: str):
        """Localiza el div cuyo texto normalizado coincide con header_text."""
        locator = self.page.locator(
            f"xpath=//div[normalize-space()='{header_text}']"
        ).first
        return locator

    def _extract_value_by_header(self, header_text: str) -> Optional[str]:
        """
        Extrae el valor asociado a un header de General Info:
        'Project Name', 'Location', 'Project Size', etc.
        """
        try:
            header = self._locate_header(header_text)
            if header.count() == 0:
                return None

            hover_area = header.locator(
                "xpath=following-sibling::div[1]"
            ).first

            if hover_area.count() == 0:
                parent = header.locator("xpath=..")
                hover_area = parent.locator(
                    "xpath=.//div[contains(@class,'hoverArea')]"
                ).first

            if hover_area.count() == 0:
                return None

            value_locator = hover_area.locator(
                "xpath=.//div[contains(@class,'value')]"
            ).first

            if value_locator.count() > 0:
                text = (value_locator.text_content() or "").strip()
            else:
                text = (hover_area.text_content() or "").strip()

            return text or None

        except Exception as e:
            logger.warning(f"[⚠️] Error extrayendo campo '{header_text}': {e}")
            return None

    # ---------------------------- DATE DUE ---------------------------- #

    def _extract_date_due(self) -> Optional[str]:
        """Extrae la fecha del bloque 'Date Due'."""
        try:
            header = self._locate_header("Date Due")
            if header.count() == 0:
                return None

            hover_area = header.locator(
                "xpath=following-sibling::div[1]"
            ).first
            if hover_area.count() == 0:
                parent = header.locator("xpath=..")
                hover_area = parent.locator(
                    "xpath=.//div[contains(@class,'hoverArea')]"
                ).first

            if hover_area.count() == 0:
                return None

            span = hover_area.locator("xpath=.//span[1]").first
            if span.count() > 0:
                visible = (span.text_content() or "").strip()
                if visible:
                    return visible

            text = (hover_area.text_content() or "").strip()
            return text or None

        except Exception as e:
            logger.warning(f"[⚠️] Error extrayendo Date Due: {e}")
            return None

    # ------------------------ PROJECT INFORMATION ------------------------ #

    def _extract_project_information(self) -> Optional[str]:
        """
        Extrae 'Project Information' (texto libre) a partir del bloque DraftJS.
        """
        try:
            header = self._locate_header("Project Information")
            if header.count() == 0:
                return None

            hover_area = header.locator(
                "xpath=following-sibling::div[1]"
            ).first
            if hover_area.count() == 0:
                parent = header.locator("xpath=..")
                hover_area = parent.locator(
                    "xpath=.//div[contains(@class,'hoverArea')]"
                ).first

            if hover_area.count() == 0:
                return None

            raw_text = hover_area.text_content() or ""
            cleaned = " ".join(raw_text.split())
            return cleaned or None

        except Exception as e:
            logger.warning(f"[⚠️] Error extrayendo Project Information: {e}")
            return None
