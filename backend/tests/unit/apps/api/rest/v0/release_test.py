from datetime import datetime
from http import HTTPStatus
from unittest.mock import MagicMock

import pytest
from django.urls import Resolver404, resolve
from ninja.responses import Response

from apps.api.rest.v0.release import (
    ReleaseDetail,
    ReleaseFilter,
    get_release,
    list_release,
)
from apps.github.models.release import Release as ReleaseModel


class TestReleaseSchema:
    @pytest.mark.parametrize(
        "release_data",
        [
            {
                "created_at": "2024-12-30T00:00:00Z",
                "description": "First stable release",
                "name": "v1.0",
                "published_at": "2024-12-30T00:00:00Z",
                "tag_name": "v1.0.0",
            },
            {
                "created_at": "2024-12-29T00:00:00Z",
                "description": "Minor improvements and bug fixes",
                "name": "v1.1",
                "published_at": "2024-12-30T00:00:00Z",
                "tag_name": "v1.1.0",
            },
        ],
    )
    def test_release_schema(self, release_data):
        release = ReleaseDetail(**release_data)

        assert release.created_at == datetime.fromisoformat(release_data["created_at"])
        assert release.description == release_data["description"]
        assert release.name == release_data["name"]
        assert release.published_at == datetime.fromisoformat(release_data["published_at"])
        assert release.tag_name == release_data["tag_name"]


class TestListRelease:
    """Tests for list_release view function."""

    def test_list_release_no_filter(self, mocker):
        """Test listing releases without filters."""
        mock_qs = MagicMock()
        mock_qs.exclude.return_value.select_related.return_value = mock_qs
        mock_qs.order_by.return_value = []
        mocker.patch(
            "apps.api.rest.v0.release.ReleaseModel.objects",
            mock_qs,
        )

        request = MagicMock()
        filters = ReleaseFilter()
        list_release(request, filters, None)

        mock_qs.order_by.assert_called_once_with("-published_at", "-created_at")

    def test_list_release_with_organization_filter(self, mocker):
        """Test listing releases with organization filter."""
        mock_qs = MagicMock()
        mock_filtered = MagicMock()
        mock_qs.exclude.return_value.select_related.return_value = mock_qs
        mock_qs.filter.return_value = mock_filtered
        mock_filtered.order_by.return_value = []
        mocker.patch(
            "apps.api.rest.v0.release.ReleaseModel.objects",
            mock_qs,
        )

        request = MagicMock()
        filters = ReleaseFilter(organization="OWASP")
        list_release(request, filters, None)

        mock_qs.filter.assert_called_with(repository__organization__login__iexact="OWASP")

    def test_list_release_with_repository_filter(self, mocker):
        """Test listing releases with repository filter."""
        mock_qs = MagicMock()
        mock_filtered = MagicMock()
        mock_qs.exclude.return_value.select_related.return_value = mock_qs
        mock_qs.filter.return_value = mock_filtered
        mock_filtered.filter.return_value = mock_filtered
        mock_filtered.order_by.return_value = []
        mocker.patch(
            "apps.api.rest.v0.release.ReleaseModel.objects",
            mock_qs,
        )

        request = MagicMock()
        filters = ReleaseFilter(organization="OWASP", repository="Nest")
        list_release(request, filters, None)

        mock_filtered.filter.assert_called_with(repository__name__iexact="Nest")

    def test_list_release_with_tag_filter(self, mocker):
        """Test listing releases with tag_name filter."""
        mock_qs = MagicMock()
        mock_qs.exclude.return_value.select_related.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs
        mock_qs.order_by.return_value = []
        mocker.patch(
            "apps.api.rest.v0.release.ReleaseModel.objects",
            mock_qs,
        )

        request = MagicMock()
        filters = ReleaseFilter(tag_name="v1.0.0")
        list_release(request, filters, None)

        mock_qs.filter.assert_called_with(tag_name="v1.0.0")

    def test_list_release_with_ordering(self, mocker):
        """Test listing releases with custom ordering."""
        mock_qs = MagicMock()
        mock_qs.exclude.return_value.select_related.return_value = mock_qs
        mock_qs.order_by.return_value = []
        mocker.patch(
            "apps.api.rest.v0.release.ReleaseModel.objects",
            mock_qs,
        )

        request = MagicMock()
        filters = ReleaseFilter()
        list_release(request, filters, "created_at")

        mock_qs.order_by.assert_called_once_with("created_at")


class TestGetRelease:
    """Tests for get_release view function."""

    def test_get_release_success(self, mocker):
        """Test getting a specific release successfully."""
        mock_release = MagicMock()
        mock_qs = MagicMock()
        mock_qs.get.return_value = mock_release
        mocker.patch(
            "apps.api.rest.v0.release.ReleaseModel.objects",
            mock_qs,
        )

        request = MagicMock()
        result = get_release(request, "OWASP", "Nest", "v1.0.0")

        assert result == mock_release
        mock_qs.get.assert_called_once_with(
            repository__organization__login__iexact="OWASP",
            repository__name__iexact="Nest",
            tag_name="v1.0.0",
        )

    def test_get_release_not_found(self, mocker):
        """Test getting a non-existent release."""
        mock_qs = MagicMock()
        mock_qs.get.side_effect = ReleaseModel.DoesNotExist
        mocker.patch(
            "apps.api.rest.v0.release.ReleaseModel.objects",
            mock_qs,
        )

        request = MagicMock()
        result = get_release(request, "OWASP", "NonExistent", "v99.0.0")

        assert isinstance(result, Response)
        assert result.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.parametrize(
        "tag_name",
        [
            "v1.0.0",
            "gopls/v0.24.0",
            "helm/chart/v1.2.3",
            "release/v2.1.0-alpha",
        ],
    )
    def test_get_release_with_slash_tag_name(self, mocker, tag_name):
        """Test getting a release whose tag contains slashes."""
        mock_release = MagicMock()
        mock_qs = MagicMock()
        mock_qs.get.return_value = mock_release
        mocker.patch(
            "apps.api.rest.v0.release.ReleaseModel.objects",
            mock_qs,
        )

        request = MagicMock()
        result = get_release(request, "OWASP", "Nest", tag_name)

        assert result == mock_release
        mock_qs.get.assert_called_once_with(
            repository__organization__login__iexact="OWASP",
            repository__name__iexact="Nest",
            tag_name=tag_name,
        )


class TestReleaseRouting:
    """Tests for release route resolution."""

    @pytest.mark.parametrize(
        ("url", "expected_org", "expected_repo", "expected_tag"),
        [
            ("/api/v0/releases/OWASP/Nest/v1.0.0", "OWASP", "Nest", "v1.0.0"),
            (
                "/api/v0/releases/golang/tools/gopls/v0.24.0",
                "golang",
                "tools",
                "gopls/v0.24.0",
            ),
            (
                "/api/v0/releases/helm/charts/sub/chart/v1.0.0",
                "helm",
                "charts",
                "sub/chart/v1.0.0",
            ),
            (
                "/api/v0/releases/OWASP/Nest/gopls%2Fv0.24.0",
                "OWASP",
                "Nest",
                "gopls%2Fv0.24.0",
            ),
        ],
    )
    def test_release_detail_url_resolves_with_slashes(
        self,
        url,
        expected_org,
        expected_repo,
        expected_tag,
    ):
        """Test that release detail route correctly captures tag names with slashes."""
        match = resolve(url)
        assert match.kwargs["organization_id"] == expected_org
        assert match.kwargs["repository_id"] == expected_repo
        assert match.kwargs["release_id"] == expected_tag

    def test_release_detail_url_empty_tag_not_matched(self):
        """Test that release detail route does not match when tag is missing."""
        with pytest.raises(Resolver404):
            resolve("/api/v0/releases/OWASP/Nest/")
