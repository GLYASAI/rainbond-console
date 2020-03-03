# -*- coding: utf-8 -*-
import logging

from django.db.models import Q

from console.exception.exceptions import ExterpriseNotExistError
from console.models.main import EnterpriseUserPerm
from console.repositories.base import BaseConnection
from console.repositories.team_repo import team_repo
from console.repositories.user_repo import user_repo
from console.repositories.user_role_repo import user_role_repo
from console.repositories.user_role_repo import UserRoleNotFoundException
from console.models.main import Applicants
from console.models.main import ServiceShareRecord

from www.models.main import TenantEnterprise
from www.models.main import TenantRegionInfo
from www.models.main import ServiceGroup
from www.models.main import ServiceGroupRelation
from www.models.main import Users
from www.models.main import Tenants
from www.models.main import PermRelTenant

logger = logging.getLogger("default")


class TenantEnterpriseRepo(object):

    def is_user_admin_in_enterprise(self, user, enterprise_id):
        """判断用户在该企业下是否为管理员"""
        if user.enterprise_id != enterprise_id:
            return False
        user_perms = enterprise_user_perm_repo.get_user_enterprise_perm(user.user_id, enterprise_id)
        if not user_perms:
            users = user_repo.get_enterprise_users(enterprise_id).order_by("user_id")
            if users:
                admin_user = users[0]
                # 如果有，判断用户最开始注册的用户和当前用户是否为同一人，如果是，添加数据返回true
                if admin_user.user_id == user.user_id:
                    enterprise_user_perm_repo.create_enterprise_user_perm(user.user_id, enterprise_id, "admin")
                    return True
                else:
                    return False
        else:
            return True

    def get_team_enterprises(self, tenant_id):
        enterprise_ids = TenantRegionInfo.objects.filter(tenant_id=tenant_id).values_list("enterprise_id", flat=True)
        return TenantEnterprise.objects.filter(enterprise_id__in=enterprise_ids)

    def get_enterprises_by_user_id(self, user_id):
        try:
            user = user_repo.get_user_by_user_id(user_id)
            tenant_ids = team_repo.get_tenants_by_user_id(user_id).values_list("tenant_id", flat=True)
            enterprise_ids = list(TenantRegionInfo.objects.filter(
                tenant_id__in=tenant_ids).values_list("enterprise_id", flat=True))
            enterprise_ids.append(user.enterprise_id)
            enterprises = TenantEnterprise.objects.filter(enterprise_id__in=enterprise_ids)
            return enterprises
        except Exception:
            raise ExterpriseNotExistError

    def get_enterprise_apps(self, enterprise_id):
        tenant_ids = TenantRegionInfo.objects.filter(enterprise_id=enterprise_id).values_list("tenant_id", flat=True)
        return ServiceGroup.objects.filter(tenant_id__in=tenant_ids)

    def get_enterprise_services(self, enterprise_id):
        tenant_ids = TenantRegionInfo.objects.filter(enterprise_id=enterprise_id).values_list("tenant_id", flat=True)
        if not tenant_ids:
            return []
        group_ids = ServiceGroup.objects.filter(tenant_id__in=tenant_ids).values_list("ID")
        if not group_ids:
            return []
        return ServiceGroupRelation.objects.filter(group_id__in=group_ids).values_list("service_id")

    def get_enterprise_users(self, enterprise_id):
        return Users.objects.filter(enterprise_id=enterprise_id)

    def get_enterprise_user_teams(self, enterprise_id, user_id, name=None):
        return team_repo.get_tenants_by_user_id_and_eid(enterprise_id, user_id, name)

    def get_enterprise_user_join_teams(self, enterprise_id, user_id):
        teams = self.get_enterprise_user_teams(enterprise_id, user_id)
        if not teams:
            return teams
        team_ids = teams.values_list("tenant_id", flat=True)
        return Applicants.objects.filter(
            user_id=user_id, is_pass=1, team_id__in=team_ids).order_by("-apply_time")

    def get_enterprise_teams(self, enterprise_id, name=None):
        if name:
            return Tenants.objects.filter(
                enterprise_id=enterprise_id, is_active=True, tenant_alias__contains=name).order_by("-create_time")
        else:
            return Tenants.objects.filter(enterprise_id=enterprise_id, is_active=True).order_by("-create_time")

    def get_enterprise_shared_app_nums(self, enterprise_id):
        teams = Tenants.objects.filter(enterprise_id=enterprise_id)
        if not teams:
            return 0
        team_ids = teams.values_list("tenant_id", flat=True)
        service_groups = ServiceGroup.objects.filter(tenant_id__in=team_ids)
        if not service_groups:
            return 0
        group_ids = service_groups.values_list("ID", flat=True)
        apps = ServiceShareRecord.objects.filter(group_id__in=group_ids, is_success=True, step=3)
        if not apps:
            return 0
        return len(set(apps.values_list("app_id", flat=True)))

    def get_enterprise_user_active_teams(self, enterprise_id, user_id):
        tenants = self.get_enterprise_user_teams(enterprise_id, user_id)
        if not tenants:
            return None
        active_tenants_list = []
        for tenant in tenants:
            user = user_repo.get_user_by_user_id(tenant.creater)
            try:
                role = user_role_repo.get_role_names(user.user_id, tenant.tenant_id)
            except UserRoleNotFoundException:
                if tenant.creater == user.user_id:
                    role = "owner"
                else:
                    role = None
            region_name_list = []
            user = user_repo.get_user_by_user_id(tenant.creater)
            region_list = team_repo.get_team_regions(tenant.tenant_id)
            if region_list:
                region_name_list = region_list.values_list("region_name", flat=True)
            active_tenants_list.append({
                "tenant_id": tenant.tenant_id,
                "team_alias": tenant.tenant_alias,
                "owner": tenant.creater,
                "owner_name": user.nick_name,
                "enterprise_id": tenant.enterprise_id,
                "create_time": tenant.create_time,
                "team_name": tenant.tenant_name,
                "region": tenant.region,
                "region_list": region_name_list,
                "num": len(ServiceGroup.objects.filter(tenant_id=tenant.tenant_id)),
                "role": role
            })
        active_tenants_list.sort(key=lambda x: x["num"])
        active_tenants_list = active_tenants_list[:3]
        return active_tenants_list

    def get_enterprise_by_enterprise_name(self, enterprise_name):
        enterprise = TenantEnterprise.objects.filter(enterprise_name=enterprise_name)
        if not enterprise:
            return None
        else:
            return enterprise[0]

    def get_enterprise_first(self):
        """
        获取第一条企业名
        :return:
        """
        enterprise = TenantEnterprise.objects.first()
        if not enterprise:
            return None
        else:
            return enterprise

    def get_enterprise_by_enterprise_id(self, enterprise_id, exception=True):
        enterprise = TenantEnterprise.objects.filter(enterprise_id=enterprise_id)
        if not enterprise:
            return None
        else:
            return enterprise[0]

    def create_enterprise(self, **params):
        return TenantEnterprise.objects.create(**params)

    def get_enterprises_by_enterprise_ids(self, eids):
        return TenantEnterprise.objects.filter(enterprise_id__in=eids)

    def get_by_enterprise_alias(self, enterprise_alias):
        return TenantEnterprise.objects.filter(enterprise_alias=enterprise_alias).first()

    def list_all(self, query):
        if query:
            return TenantEnterprise.objects.filter(Q(enterprise_name__contains=query) |
                                                   Q(enterprise_alias__contains=query)).all()
        return TenantEnterprise.objects.all()

    def update(self, eid, **data):
        TenantEnterprise.objects.filter(enterprise_id=eid).update(**data)

    def list_appstore_infos(self, query="", page=None, page_size=None):
        limit = ""
        if page is not None and page_size is not None:
            page = page if page > 0 else 1
            page = (page - 1) * page_size
            limit = "Limit {page}, {size}".format(page=page, size=page_size)
        where = ""
        if query:
            where = "WHERE a.enterprise_alias LIKE '%{query}%' OR a.enterprise_name LIKE '%{query}%'".format(
                query=query)
        sql = """
        SELECT
            a.enterprise_id,
            a.enterprise_name,
            a.enterprise_alias,
            b.access_url
        FROM
            tenant_enterprise a
            JOIN tenant_enterprise_token b ON a.id = b.enterprise_id
        {where}
        {limit}
        """.format(where=where, limit=limit)

        conn = BaseConnection()
        result = conn.query(sql)
        return result

    def count_appstore_infos(self, query=""):
        where = ""
        if query:
            where = "WHERE a.enterprise_alias LIKE '%{query}%' OR a.enterprise_name LIKE '%{query}%'".format(
                query=query)
        sql = """
        SELECT
            count(*) as total
        FROM
            tenant_enterprise a
            JOIN tenant_enterprise_token b ON a.id = b.enterprise_id
        {where}
        """.format(where=where)

        conn = BaseConnection()
        result = conn.query(sql)
        return result[0]["total"]

    def get_enterprise_user_request_join(self, enterprise_id, user_id):
        team_ids = self.get_enterprise_teams(enterprise_id).values_list("tenant_id", flat=True)
        return Applicants.objects.filter(
            user_id=user_id, team_id__in=team_ids).order_by("is_pass", "-apply_time")

    def get_enterprise_tenant_ids(self, enterprise_id, user=None):
        if user is None:
            teams = Tenants.objects.filter(enterprise_id=enterprise_id)
            if not teams:
                return None
            team_ids = teams.values_list("tenant_id", flat=True)
        elif self.is_user_admin_in_enterprise(user, enterprise_id):
            teams = Tenants.objects.filter(enterprise_id=enterprise_id)
            if not teams:
                return None
            team_ids = teams.values_list("tenant_id", flat=True)
        else:
            enterprise = enterprise_repo.get_enterprise_by_enterprise_id(enterprise_id)
            if not enterprise:
                return None
            user_teams_perm = PermRelTenant.objects.filter(enterprise_id=enterprise.ID, user_id=user.ID)
            if not user_teams_perm:
                return None
            tenant_auto_ids = user_teams_perm.values_list("tenant_id", flat=True)
            teams = Tenants.objects.filter(ID__in=tenant_auto_ids)
            if not teams:
                return None
            team_ids = teams.values_list("tenant_id", flat=True)
        tenants = TenantRegionInfo.objects.filter(tenant_id__in=team_ids)
        if not tenants:
            return None
        else:
            return tenants.values_list("region_tenant_id", flat=True)

    def get_enterprise_app_list(self, enterprise_id, user, name, page, page_size):
        tenant_ids = self.get_enterprise_tenant_ids(enterprise_id, user)
        if not tenant_ids:
            return None, 0
        where = 'WHERE A.tenant_id in ({}) '.format(','.join(map(lambda x: '"' + x + '"', tenant_ids)))
        if name:
            where += 'AND (A.group_name LIKE "{}%" OR C.service_cname LIKE "{}%") '.format(name, name)
        limit = "LIMIT {page}, {page_size}".format(page=page-1, page_size=page_size)
        conn = BaseConnection()
        before_sql1 = """SET GLOBAL group_concat_max_len = 1024000;"""
        before_sql2 = """SET SESSION group_concat_max_len = 1024000;"""
        sql = """
            SELECT
                A.ID,
                A.group_name,
                A.tenant_id,
                CONCAT('[',
                    GROUP_CONCAT(
                    CONCAT('{"service_cname":"',C.service_cname,'"'),',',
                    CONCAT('"service_id":"',C.service_id,'"'),',',
                    CONCAT('"service_key":"',C.service_key,'"'),',',
                    CONCAT('"service_alias":"',C.service_alias),'"}')
                ,']') AS service_list
            FROM service_group A
            LEFT JOIN service_group_relation B
            ON A.ID = B.group_id AND A.tenant_id = B.tenant_id
            LEFT JOIN tenant_service C
            ON B.service_id = C.service_id AND B.tenant_id = C.tenant_id
            """
        sql += where + "GROUP BY A.ID "
        sql1 = sql
        sql += limit
        conn.query(before_sql1)
        conn.query(before_sql2)
        count = len(conn.query(sql1))
        result = conn.query(sql)
        return result, count


class TenantEnterpriseUserPermRepo(object):
    def create_enterprise_user_perm(self, user_id, enterprise_id, identity, token=None):
        if token is None:
            return EnterpriseUserPerm.objects.create(user_id=user_id, enterprise_id=enterprise_id, identity=identity)
        else:
            return EnterpriseUserPerm.objects.create(
                user_id=user_id, enterprise_id=enterprise_id, identity=identity, token=token)

    def get_user_enterprise_perm(self, user_id, enterprise_id):
        return EnterpriseUserPerm.objects.filter(user_id=user_id, enterprise_id=enterprise_id)

    def get_backend_enterprise_admin_by_user_id(self, user_id):
        """
        管理后台查询企业管理员，只有一个企业
        :param user_id:
        :param enterprise_id:
        :return:
        """
        enter_admin = EnterpriseUserPerm.objects.filter(user_id=user_id).first()
        if enter_admin:
            return enter_admin
        else:
            return None

    def count_by_eid(self, eid):
        return EnterpriseUserPerm.objects.filter(enterprise_id=eid).count()

    def delete_backend_enterprise_admin_by_user_id(self, user_id):
        """
        管理后台删除企业管理员，只有一个企业
        :param user_id:
        :param enterprise_id:
        :return:
        """
        EnterpriseUserPerm.objects.filter(user_id=user_id).delete()

    def get_by_token(self, token):
        return EnterpriseUserPerm.objects.filter(token=token).first()


enterprise_repo = TenantEnterpriseRepo()
enterprise_user_perm_repo = TenantEnterpriseUserPermRepo()
