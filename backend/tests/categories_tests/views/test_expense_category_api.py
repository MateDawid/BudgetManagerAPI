import pytest
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from factory.base import FactoryMetaClass
from rest_framework import status
from rest_framework.test import APIClient

from budgets.models.budget_model import Budget
from categories.models.expense_category_model import ExpenseCategory
from categories.models.transfer_category_model import TransferCategory
from categories.serializers.expense_category_serializer import ExpenseCategorySerializer


def categories_url(budget_id):
    """Create and return an ExpenseCategory detail URL."""
    return reverse("budgets:expense_category-list", args=[budget_id])


def category_detail_url(budget_id, category_id):
    """Create and return an ExpenseCategory detail URL."""
    return reverse("budgets:expense_category-detail", args=[budget_id, category_id])


@pytest.mark.django_db
class TestExpenseCategoryViewSetList:
    """Tests for list view on ExpenseCategoryViewSet."""

    def test_auth_required(self, api_client: APIClient, budget: Budget):
        """
        GIVEN: Budget model instance in database.
        WHEN: ExpenseCategoryViewSet list view called with GET without authentication.
        THEN: Unauthorized HTTP 401 returned.
        """
        res = api_client.get(categories_url(budget.id))

        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_not_budget_member(
        self, api_client: APIClient, user_factory: FactoryMetaClass, budget_factory: FactoryMetaClass
    ):
        """
        GIVEN: Budget model instance in database.
        WHEN: ExpenseCategoryViewSet list view called with GET by User not belonging to given Budget.
        THEN: Forbidden HTTP 403 returned.
        """
        budget_owner = user_factory()
        other_user = user_factory()
        budget = budget_factory(owner=budget_owner)
        api_client.force_authenticate(other_user)

        response = api_client.get(categories_url(budget.id))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "User does not have access to Budget."

    def test_retrieve_category_list(
        self,
        api_client: APIClient,
        base_user: AbstractUser,
        budget_factory: FactoryMetaClass,
        expense_category_factory: FactoryMetaClass,
    ):
        """
        GIVEN: Two ExpenseCategory model instances for single Budget created in database.
        WHEN: ExpenseCategoryViewSet called by Budget owner.
        THEN: Response with serialized Budget ExpenseCategory list returned.
        """
        budget = budget_factory(owner=base_user)
        api_client.force_authenticate(base_user)
        for _ in range(2):
            expense_category_factory(budget=budget)

        response = api_client.get(categories_url(budget.id))

        categories = ExpenseCategory.objects.filter(budget=budget)
        serializer = ExpenseCategorySerializer(categories, many=True)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == serializer.data

    def test_categories_list_limited_to_budget(
        self,
        api_client: APIClient,
        base_user: AbstractUser,
        budget_factory: FactoryMetaClass,
        expense_category_factory: FactoryMetaClass,
    ):
        """
        GIVEN: Two ExpenseCategory model instances for different Budgets created in database.
        WHEN: ExpenseCategoryViewSet called by one of Budgets owner.
        THEN: Response with serialized ExpenseCategory list (only from given Budget) returned.
        """
        budget = budget_factory(owner=base_user)
        category = expense_category_factory(budget=budget)
        expense_category_factory()
        api_client.force_authenticate(base_user)

        response = api_client.get(categories_url(budget.id))

        categories = ExpenseCategory.objects.filter(budget=budget)
        serializer = ExpenseCategorySerializer(categories, many=True)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == len(serializer.data) == categories.count() == 1
        assert response.data["results"] == serializer.data
        assert response.data["results"][0]["id"] == category.id

    def test_income_categories_not_in_expense_categories_list(
        self,
        api_client: APIClient,
        base_user: AbstractUser,
        budget_factory: FactoryMetaClass,
        expense_category_factory: FactoryMetaClass,
        income_category_factory: FactoryMetaClass,
    ):
        """
        GIVEN: One ExpenseCategory and one IncomeCategory models instances for the same Budget created in database.
        WHEN: ExpenseCategoryViewSet called by one of Budgets owner.
        THEN: Response with serialized ExpenseCategory list (only from given Budget) returned without IncomeCategory.
        """
        budget = budget_factory(owner=base_user)
        expense_category_factory(budget=budget)
        income_category = income_category_factory(budget=budget)
        api_client.force_authenticate(base_user)

        response = api_client.get(categories_url(budget.id))

        expense_categories = ExpenseCategory.objects.filter(budget=budget)
        serializer = ExpenseCategorySerializer(expense_categories, many=True)
        assert TransferCategory.objects.all().count() == 2
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == len(serializer.data) == expense_categories.count() == 1
        assert response.data["results"] == serializer.data
        assert income_category.id not in [category["id"] for category in response.data["results"]]


# @pytest.mark.django_db
# class TestExpenseCategoryViewSetCreate:
#     """Tests for create ExpenseCategory on ExpenseCategoryViewSet."""
#
#     PAYLOAD = {
#         "name": "Supermarket",
#         "description": "Supermarket in which I buy food.",
#         "is_active": True,
#         "is_deposit": False,
#     }
#
#     def test_auth_required(self, api_client: APIClient, budget: Budget):
#         """
#         GIVEN: Budget model instance in database.
#         WHEN: ExpenseCategoryViewSet list view called with POST without authentication.
#         THEN: Unauthorized HTTP 401 returned.
#         """
#         res = api_client.post(categories_url(budget.id), data={})
#
#         assert res.status_code == status.HTTP_401_UNAUTHORIZED
#
#     def test_user_not_budget_member(
#         self, api_client: APIClient, user_factory: FactoryMetaClass, budget_factory: FactoryMetaClass
#     ):
#         """
#         GIVEN: Budget model instance in database.
#         WHEN: ExpenseCategoryViewSet list view called with POST by User not belonging to given Budget.
#         THEN: Forbidden HTTP 403 returned.
#         """
#         budget_owner = user_factory()
#         other_user = user_factory()
#         budget = budget_factory(owner=budget_owner)
#         api_client.force_authenticate(other_user)
#
#         response = api_client.post(categories_url(budget.id), data={})
#
#         assert response.status_code == status.HTTP_403_FORBIDDEN
#         assert response.data["detail"] == "User does not have access to Budget."
#
#     def test_create_single_category(
#         self, api_client: APIClient, base_user: AbstractUser, budget_factory: FactoryMetaClass
#     ):
#         """
#         GIVEN: Budget instance created in database. Valid payload prepared for ExpenseCategory.
#         WHEN: ExpenseCategoryViewSet called with POST by User belonging to Budget with valid payload.
#         THEN: ExpenseCategory object created in database with given payload
#         """
#         budget = budget_factory(owner=base_user)
#         api_client.force_authenticate(base_user)
#
#         response = api_client.post(categories_url(budget.id), self.PAYLOAD)
#
#         assert response.status_code == status.HTTP_201_CREATED
#         assert ExpenseCategory.objects.filter(budget=budget).count() == 1
#         assert ExpenseCategory.deposits.filter(budget=budget).count() == 0
#         category = ExpenseCategory.objects.get(id=response.data["id"])
#         assert category.budget == budget
#         for key in self.PAYLOAD:
#             assert getattr(category, key) == self.PAYLOAD[key]
#         serializer = ExpenseCategorySerializer(category)
#         assert response.data == serializer.data
#
#     def test_create_single_deposit(
#         self, api_client: APIClient, base_user: AbstractUser, budget_factory: FactoryMetaClass
#     ):
#         """
#         GIVEN: Budget instance created in database. Valid payload with is_deposit=True prepared for ExpenseCategory.
#         WHEN: ExpenseCategoryViewSet called with POST by User belonging to Budget with valid payload.
#         THEN: ExpenseCategory object with is_deposit=True created in database with given payload
#         """
#         budget = budget_factory(owner=base_user)
#         api_client.force_authenticate(base_user)
#         payload = self.PAYLOAD.copy()
#         payload["is_deposit"] = True
#
#         response = api_client.post(categories_url(budget.id), payload)
#
#         assert response.status_code == status.HTTP_201_CREATED
#         assert ExpenseCategory.objects.filter(budget=budget).count() == 1
#         assert ExpenseCategory.deposits.filter(budget=budget).count() == 1
#         category = ExpenseCategory.objects.get(id=response.data["id"])
#         assert category.budget == budget
#         for key in payload:
#             assert getattr(category, key) == payload[key]
#         serializer = ExpenseCategorySerializer(category)
#         assert response.data == serializer.data
#
#     @pytest.mark.parametrize("field_name", ["name", "description"])
#     def test_error_value_too_long(
#         self, api_client: APIClient, base_user: AbstractUser, budget_factory: FactoryMetaClass, field_name: str
#     ):
#         """
#         GIVEN: Budget instance created in database. Payload for ExpenseCategory with field value too long.
#         WHEN: ExpenseCategoryViewSet called with POST by User belonging to Budget with invalid payload.
#         THEN: Bad request HTTP 400 returned. ExpenseCategory not created in database.
#         """
#         budget = budget_factory(owner=base_user)
#         api_client.force_authenticate(base_user)
#         max_length = ExpenseCategory._meta.get_field(field_name).max_length
#         payload = self.PAYLOAD.copy()
#         payload[field_name] = (max_length + 1) * "a"
#
#         response = api_client.post(categories_url(budget.id), payload)
#
#         assert response.status_code == status.HTTP_400_BAD_REQUEST
#         assert field_name in response.data["detail"]
#         assert response.data["detail"][field_name][0] == f"Ensure this field has no more
#         than {max_length} characters."
#         assert not ExpenseCategory.objects.filter(budget=budget).exists()
#
#     def test_error_name_already_used(
#         self, api_client: APIClient, base_user: AbstractUser, budget_factory: FactoryMetaClass
#     ):
#         """
#         GIVEN: Budget instance created in database. Valid payload for ExpenseCategory.
#         WHEN: ExpenseCategoryViewSet called twice with POST by User belonging to Budget with the same payload.
#         THEN: Bad request HTTP 400 returned. Only one ExpenseCategory created in database.
#         """
#         budget = budget_factory(owner=base_user)
#         api_client.force_authenticate(base_user)
#         payload = self.PAYLOAD.copy()
#
#         api_client.post(categories_url(budget.id), payload)
#         response = api_client.post(categories_url(budget.id), payload)
#
#         assert response.status_code == status.HTTP_400_BAD_REQUEST
#         assert "name" in response.data["detail"]
#         assert response.data["detail"]["name"][0] == "ExpenseCategory with given name already exists in Budget."
#         assert ExpenseCategory.objects.filter(budget=budget).count() == 1
#
#
# @pytest.mark.django_db
# class TestExpenseCategoryViewSetDetail:
#     """Tests for detail view on ExpenseCategoryViewSet."""
#
#     def test_auth_required(self, api_client: APIClient, category: ExpenseCategory):
#         """
#         GIVEN: Budget model instance in database.
#         WHEN: ExpenseCategoryViewSet detail view called with GET without authentication.
#         THEN: Unauthorized HTTP 401 returned.
#         """
#         res = api_client.get(category_detail_url(category.budget.id, category.id), data={})
#
#         assert res.status_code == status.HTTP_401_UNAUTHORIZED
#
#     def test_user_not_budget_member(
#         self,
#         api_client: APIClient,
#         user_factory: FactoryMetaClass,
#         budget_factory: FactoryMetaClass,
#         expense_category_factory: FactoryMetaClass,
#     ):
#         """
#         GIVEN: Budget model instance in database.
#         WHEN: ExpenseCategoryViewSet detail view called with GET by User not belonging to given Budget.
#         THEN: Forbidden HTTP 403 returned.
#         """
#         budget_owner = user_factory()
#         other_user = user_factory()
#         budget = budget_factory(owner=budget_owner)
#         category = expense_category_factory(budget=budget)
#         api_client.force_authenticate(other_user)
#         url = category_detail_url(category.budget.id, category.id)
#
#         response = api_client.get(url)
#
#         assert response.status_code == status.HTTP_403_FORBIDDEN
#         assert response.data["detail"] == "User does not have access to Budget."
#
#     def test_get_category_details(
#         self,
#         api_client: APIClient,
#         base_user: AbstractUser,
#         budget_factory: FactoryMetaClass,
#         expense_category_factory: FactoryMetaClass,
#     ):
#         """
#         GIVEN: ExpenseCategory instance for Budget created in database.
#         WHEN: ExpenseCategoryViewSet detail view called by User belonging to Budget.
#         THEN: HTTP 200, ExpenseCategory details returned.
#         """
#         budget = budget_factory(owner=base_user)
#         category = expense_category_factory(budget=budget)
#         api_client.force_authenticate(base_user)
#         url = category_detail_url(budget.id, category.id)
#
#         response = api_client.get(url)
#         serializer = ExpenseCategorySerializer(category)
#
#         assert response.status_code == status.HTTP_200_OK
#         assert response.data == serializer.data
#
#
# @pytest.mark.django_db
# class TestExpenseCategoryViewSetUpdate:
#     """Tests for update view on ExpenseCategoryViewSet."""
#
#     PAYLOAD = {
#         "name": "Supermarket",
#         "description": "Supermarket in which I buy food.",
#         "is_active": True,
#         "is_deposit": False,
#     }
#
#     def test_auth_required(self, api_client: APIClient, category: ExpenseCategory):
#         """
#         GIVEN: Budget model instance in database.
#         WHEN: ExpenseCategoryViewSet detail view called with PATCH without authentication.
#         THEN: Unauthorized HTTP 401 returned.
#         """
#         res = api_client.patch(category_detail_url(category.budget.id, category.id), data={})
#
#         assert res.status_code == status.HTTP_401_UNAUTHORIZED
#
#     def test_user_not_budget_member(
#         self,
#         api_client: APIClient,
#         user_factory: FactoryMetaClass,
#         budget_factory: FactoryMetaClass,
#         expense_category_factory: FactoryMetaClass,
#     ):
#         """
#         GIVEN: Budget model instance in database.
#         WHEN: ExpenseCategoryViewSet detail view called with PATCH by User not belonging to given Budget.
#         THEN: Forbidden HTTP 403 returned.
#         """
#         budget_owner = user_factory()
#         other_user = user_factory()
#         budget = budget_factory(owner=budget_owner)
#         category = expense_category_factory(budget=budget)
#         api_client.force_authenticate(other_user)
#         url = category_detail_url(category.budget.id, category.id)
#
#         response = api_client.patch(url)
#
#         assert response.status_code == status.HTTP_403_FORBIDDEN
#         assert response.data["detail"] == "User does not have access to Budget."
#
#     @pytest.mark.parametrize(
#         "param, value",
#         [
#             ("name", "New name"),
#             ("description", "New description"),
#             ("is_active", not PAYLOAD["is_active"]),
#             ("is_deposit", not PAYLOAD["is_deposit"]),
#         ],
#     )
#     @pytest.mark.django_db
#     def test_category_update(
#         self,
#         api_client: APIClient,
#         base_user: AbstractUser,
#         budget_factory: FactoryMetaClass,
#         expense_category_factory: FactoryMetaClass,
#         param: str,
#         value: Any,
#     ):
#         """
#         GIVEN: ExpenseCategory instance for Budget created in database.
#         WHEN: ExpenseCategoryViewSet detail view called with PATCH by User belonging to Budget.
#         THEN: HTTP 200, ExpenseCategory updated.
#         """
#         budget = budget_factory(owner=base_user)
#         category = expense_category_factory(budget=budget, **self.PAYLOAD)
#         update_payload = {param: value}
#         api_client.force_authenticate(base_user)
#         url = category_detail_url(budget.id, category.id)
#
#         response = api_client.patch(url, update_payload)
#
#         assert response.status_code == status.HTTP_200_OK
#         category.refresh_from_db()
#         assert getattr(category, param) == update_payload[param]
#
#     @pytest.mark.parametrize("param, value", [("name", PAYLOAD["name"])])
#     def test_error_on_category_update(
#         self,
#         api_client: APIClient,
#         base_user: Any,
#         budget_factory: FactoryMetaClass,
#         expense_category_factory: FactoryMetaClass,
#         param: str,
#         value: Any,
#     ):
#         """
#         GIVEN: ExpenseCategory instance for Budget created in database. Update payload with invalid value.
#         WHEN: ExpenseCategoryViewSet detail view called with PATCH by User belonging to Budget
#         with invalid payload.
#         THEN: Bad request HTTP 400, ExpenseCategory not updated.
#         """
#         budget = budget_factory(owner=base_user)
#         expense_category_factory(budget=budget, **self.PAYLOAD)
#         category = expense_category_factory(budget=budget)
#         old_value = getattr(category, param)
#         update_payload = {param: value}
#         api_client.force_authenticate(base_user)
#         url = category_detail_url(budget.id, category.id)
#
#         response = api_client.patch(url, update_payload)
#
#         assert response.status_code == status.HTTP_400_BAD_REQUEST
#         category.refresh_from_db()
#         assert getattr(category, param) == old_value
#
#     def test_category_update_many_fields(
#         self,
#         api_client: APIClient,
#         base_user: AbstractUser,
#         budget_factory: FactoryMetaClass,
#         expense_category_factory: FactoryMetaClass,
#     ):
#         """
#         GIVEN: ExpenseCategory instance for Budget created in database. Valid payload with many params.
#         WHEN: ExpenseCategoryViewSet detail endpoint called with PATCH.
#         THEN: HTTP 200 returned. ExpenseCategory updated in database.
#         """
#         budget = budget_factory(owner=base_user)
#         api_client.force_authenticate(base_user)
#         payload = self.PAYLOAD.copy()
#         category = expense_category_factory(budget=budget, **payload)
#         update_payload = {
#             "name": "Some market",
#             "description": "Updated supermarket description.",
#             "is_active": False,
#             "is_deposit": True,
#         }
#         url = category_detail_url(category.budget.id, category.id)
#
#         response = api_client.patch(url, update_payload)
#
#         assert response.status_code == status.HTTP_200_OK
#         category.refresh_from_db()
#         for param, value in update_payload.items():
#             assert getattr(category, param) == value
#
#
# @pytest.mark.django_db
# class TestExpenseCategoryViewSetDelete:
#     """Tests for delete ExpenseCategory on ExpenseCategoryViewSet."""
#
#     def test_auth_required(self, api_client: APIClient, base_user: AbstractUser,
#     expense_category_factory: FactoryMetaClass):
#         """
#         GIVEN: ExpenseCategory instance for Budget created in database.
#         WHEN: ExpenseCategoryViewSet detail view called with PUT without authentication.
#         THEN: Unauthorized HTTP 401.
#         """
#         category = expense_category_factory()
#         url = category_detail_url(category.budget.id, category.id)
#
#         response = api_client.delete(url)
#
#         assert response.status_code == status.HTTP_401_UNAUTHORIZED
#
#     def test_user_not_budget_member(
#         self,
#         api_client: APIClient,
#         base_user: AbstractUser,
#         budget_factory: FactoryMetaClass,
#         expense_category_factory: FactoryMetaClass,
#     ):
#         """
#         GIVEN: ExpenseCategory instance for Budget created in database.
#         WHEN: ExpenseCategoryViewSet detail view called with DELETE by User not belonging to Budget.
#         THEN: Forbidden HTTP 403 returned.
#         """
#         category = expense_category_factory(budget=budget_factory())
#         api_client.force_authenticate(base_user)
#         url = category_detail_url(category.budget.id, category.id)
#
#         response = api_client.delete(url)
#
#         assert response.status_code == status.HTTP_403_FORBIDDEN
#         assert response.data["detail"] == "User does not have access to Budget."
#
#     def test_delete_category(
#         self,
#         api_client: APIClient,
#         base_user: Any,
#         budget_factory: FactoryMetaClass,
#         expense_category_factory: FactoryMetaClass,
#     ):
#         """
#         GIVEN: ExpenseCategory instance for Budget created in database.
#         WHEN: ExpenseCategoryViewSet detail view called with DELETE by User belonging to Budget.
#         THEN: No content HTTP 204, ExpenseCategory deleted.
#         """
#         budget = budget_factory(owner=base_user)
#         category = expense_category_factory(budget=budget)
#         api_client.force_authenticate(base_user)
#         url = category_detail_url(budget.id, category.id)
#
#         assert budget.categories.all().count() == 1
#
#         response = api_client.delete(url)
#
#         assert response.status_code == status.HTTP_204_NO_CONTENT
#         assert not budget.categories.all().exists()
