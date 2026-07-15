from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel



class LengthConfig(BaseModel):
    wordRange: str
    readingTime: str
    density: str


class DocumentTypeConfig(BaseModel):
    tone: str
    length: LengthConfig
    structure: List[str]


class AudienceConfig(BaseModel):
    defaultType: str
    documentTypes: Dict[str, DocumentTypeConfig]


class AnalysisConfigModel(BaseModel):
    config: Dict[str, AudienceConfig]

    def available_document_types(self, audience: str) -> List[str]:
        cfg = self.config.get(audience, self.config.get("internal"))
        return list(cfg.documentTypes.keys())

    def default_document_type(self, audience: str) -> str:
        cfg = self.config.get(audience, self.config.get("internal"))
        return cfg.defaultType

    def get_config(self, audience: str, document_type: Optional[str] = None) -> dict:
        cfg = self.config.get(audience, self.config.get("internal"))
        dt = document_type if document_type in cfg.documentTypes else cfg.defaultType
        return {
            "audience": audience,
            "document_type": dt,
            "config": cfg.documentTypes[dt].dict(),
            "default_type": cfg.defaultType,
        }

