import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SubmissionStatus(str, enum.Enum):
    submitted = "submitted"
    analyzing = "analyzing"
    completed = "completed"
    failed = "failed"


class SubmissionFileRole(str, enum.Enum):
    primary = "primary"
    supporting = "supporting"


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), unique=True, nullable=False,
    )
    primary_file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploaded_files.id"), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status", native_enum=False),
        default=SubmissionStatus.submitted,
        nullable=False,
    )

    workspace = relationship("Workspace", back_populates="submission")
    primary_file = relationship("UploadedFile", foreign_keys=[primary_file_id])
    submission_files = relationship("SubmissionFile", back_populates="submission", lazy="selectin")
    analysis_runs = relationship("AnalysisRun", back_populates="submission", lazy="selectin")


class SubmissionFile(Base):
    __tablename__ = "submission_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("submissions.id"), nullable=False)
    file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploaded_files.id"), nullable=False)
    role: Mapped[SubmissionFileRole] = mapped_column(
        Enum(SubmissionFileRole, name="submission_file_role", native_enum=False),
        nullable=False,
    )

    submission = relationship("Submission", back_populates="submission_files")
    file = relationship("UploadedFile")
