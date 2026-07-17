# Database Backups — Setup & Use

After today, this is the safety net so "did I lose my data?" is never a worry again.
Two scripts: `backup.sh` (make a backup) and `restore.sh` (restore one).

## One-time setup
1. The scripts live in `~/SecOps--Audit/`. Make them executable:
       chmod +x backup.sh restore.sh
2. Test a manual backup right now:
       ./backup.sh
   It writes a file to ~/backups/ — confirm you see it:
       ls -lh ~/backups/

## Daily automatic backup (cron)
Run `crontab -e` and add this line (daily at 2 AM):

    0 2 * * * /home/ubuntu/SecOps--Audit/backup.sh >> /home/ubuntu/backups/backup.log 2>&1

That keeps 14 days of local backups automatically (configurable via RETAIN_DAYS).

## Back up OFF the server too (S3) — do this before real customers
Local backups don't protect against losing the whole server. Push them to S3:

1. Install + configure AWS CLI (use an IAM key allowed to write to your bucket):
       sudo apt-get install -y awscli
       aws configure
2. Set your bucket and run with --s3:
       export S3_BUCKET=s3://your-backup-bucket/codecore
       ./backup.sh --s3
3. For the cron job, set S3_BUCKET in the crontab line:
       0 2 * * * S3_BUCKET=s3://your-backup-bucket/codecore /home/ubuntu/SecOps--Audit/backup.sh >> /home/ubuntu/backups/backup.log 2>&1

## Restore from a backup
    ./restore.sh ~/backups/codecore-secops-YYYYMMDD-HHMMSS.sql.gz
(asks for confirmation, then overwrites the current DB with the backup)

## Habits that make data loss impossible
- Run `./backup.sh` BEFORE any risky change (rebuilds, branch switches, experiments).
- Let the daily cron run for routine safety.
- Before onboarding any real customer: turn on the S3 upload, and do ONE test
  restore so you KNOW it works (an untested backup is not a backup).

## Honest note
A backup you've never restored is a hope, not a guarantee. Once set up, do one
practice restore (into a throwaway DB or right after a fresh deploy) so you've
proven the whole loop works. Then you can truly stop worrying about data loss.
