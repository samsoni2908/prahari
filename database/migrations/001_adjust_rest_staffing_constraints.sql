-- Migration 001: Adjust rest_records and staffing check constraints for operational semantics
-- rest_records: allow negative turnaround deficits
ALTER TABLE rest_records DROP CONSTRAINT IF EXISTS rest_records_rest_hours_check;
ALTER TABLE rest_records DROP CONSTRAINT IF EXISTS rest_records_rest_gap_hours_check;
ALTER TABLE rest_records ALTER COLUMN rest_hours TYPE NUMERIC(6,2);

-- staffing: allow surplus staffing coverage above 100%
ALTER TABLE staffing DROP CONSTRAINT IF EXISTS staffing_coverage_percent_check;
ALTER TABLE staffing ADD CONSTRAINT staffing_coverage_percent_check CHECK (coverage_percent >= 0);
