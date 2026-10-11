from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class BzpNoticeDTO(BaseModel):
    model_config = ConfigDict(extra="allow")

    bzpNumber: Optional[str] = None
    noticeNumber: Optional[str] = None
    noticeType: Optional[str] = None
    orderObject: Optional[str] = None
    organizationName: Optional[str] = None
    organizationNationalId: Optional[str] = None
    publicationDate: Optional[str] = None
    submittingOffersDate: Optional[str] = None
    objectId: Optional[str] = None

    # Additional confirmed official fields from e-Zamówienia BZP API
    orderType: Optional[str] = None
    tenderId: Optional[str] = None
    htmlBody: Optional[str] = None
    cpvCode: Optional[str] = None
    cpvCodes: Optional[list[str]] = None
    organizationCity: Optional[str] = None
    organizationProvince: Optional[str] = None
    estimatedValue: Optional[float] = None
    currency: Optional[str] = None
