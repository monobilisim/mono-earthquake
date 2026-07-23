ALTER TABLE `wa_messages` ADD `reminder_count` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `wa_messages` ADD `read_at` integer DEFAULT NULL;--> statement-breakpoint
ALTER TABLE `wa_messages` ADD `reply_at` integer DEFAULT NULL;