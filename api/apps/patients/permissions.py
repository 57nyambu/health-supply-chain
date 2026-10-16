from apps.access.catalogue import PermissionDef as P
from apps.access.catalogue import Sensitivity as S

PERMISSIONS = [
    P("patients.patient.search", "Search the patient registry", S.PHI),
    P("patients.patient.read", "View patient demographics, identifiers and contacts", S.PHI),
    P("patients.patient.create", "Register a patient", S.PHI),
    P("patients.patient.update", "Update patient demographics and contacts", S.PHI),
    P(
        "patients.patient.register_unidentified",
        "Quick-register an unidentified emergency patient",
        S.PHI,
    ),
    P(
        "patients.duplicate.override",
        "Create a record despite a likely duplicate, with a reason",
        S.PHI,
    ),
    P("patients.registry.search", "Search the national Client Registry", S.PHI),
    P("patients.registry.import", "Import a Client Registry match into a local record", S.PHI),
    P("patients.consent.record", "Record privacy-notice acknowledgement and consents", S.PHI),
    P("patients.merge.request", "Request a patient merge or unmerge", S.PHI),
    P("patients.merge.approve", "Approve a patient merge or unmerge", S.PHI, privileged=True),
    P("patients.dsar.read", "View data subject requests", S.PHI),
    P("patients.dsar.process", "Process data subject requests and produce exports", S.PHI),
]
