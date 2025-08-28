from home.enums import ApprovalStatus
from home.models import LarkApprovalInstance
from util import time_util


def new_approval_instance(approval_code, instance_code, approval_name, submitter, detail):
    if LarkApprovalInstance.objects.filter(instance_code=instance_code).count() == 0:
        instance = LarkApprovalInstance(approval_code=approval_code, instance_code=instance_code,
                                        approval_name=approval_name, submitter=submitter, detail=detail,
                                        submit_time=time_util.get_cnt_now(),
                                        approval_status=ApprovalStatus.PENDING.value,
                                        approval_time=time_util.get_cnt_min_time(), deleted=0)
        instance.save()


def mod_approval(instance_code, approval_status):
    LarkApprovalInstance.objects.filter(instance_code=instance_code).update(approval_status=approval_status.value,
                                                                            approval_time=time_util.get_cnt_now())
