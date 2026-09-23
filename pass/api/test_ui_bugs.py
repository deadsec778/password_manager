from bs4 import BeautifulSoup
import pytest

# TDD: We want to make sure the modal is not trapped inside the ul list.
# We also want to make sure the search result templates have an actual anchor linking to the vault.

def test_admin_logs_modal_not_in_list():
    with open("pass/api/templates/admin_logs.html", "r", encoding="utf-8") as f:
        html = f.read()

    # The issue: modal shouldn't be inside the UL.
    soup = BeautifulSoup(html, "html.parser")
    ul = soup.find("ul", class_="list-group")
    
    # Check if there are modals inside the ul
    modals_in_ul = ul.find_all("div", class_="modal")
    assert len(modals_in_ul) == 0, "Modals should not be placed inside the list group items"

def test_search_results_have_links():
    with open("pass/api/templates/dashboard.html", "r", encoding="utf-8") as f:
        html = f.read()
    
    # Locate the javascript part generating results
    # We expect something like <a href="/vaults/${p.vault_id}#pwcell_${p.password_id}"
    assert "<a " in html and "${p.vault_id}" in html, "Search results in JS must generate clickable <a> links"
    assert "href=" in html, "Search results must have href"

