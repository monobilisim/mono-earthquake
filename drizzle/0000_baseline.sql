CREATE TABLE IF NOT EXISTS `earthquakes` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`timestamp` text NOT NULL,
	`date` text NOT NULL,
	`time` text NOT NULL,
	`latitude` real NOT NULL,
	`longitude` real NOT NULL,
	`depth` real NOT NULL,
	`md` real,
	`ml` real,
	`mw` real,
	`magnitude` real,
	`location` text NOT NULL,
	`quality` text NOT NULL,
	`year` integer NOT NULL,
	`month` integer NOT NULL,
	`day` integer NOT NULL,
	`week` integer NOT NULL,
	`created_at` numeric DEFAULT (CURRENT_TIMESTAMP) NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `groups` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`name` text(255) NOT NULL,
	`polls` text(255) DEFAULT (NULL),
	`active` numeric DEFAULT 1 NOT NULL,
	`created_at` numeric DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	`updated_at` numeric DEFAULT (CURRENT_TIMESTAMP) NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `polls` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`name` text(255) NOT NULL,
	`type` text(255) NOT NULL,
	`threshold` real DEFAULT (NULL),
	`created_at` numeric DEFAULT (CURRENT_TIMESTAMP) NOT NULL
);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS `idx_polls_name` ON `polls` (`name`);--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `sessions` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`user_id` integer NOT NULL,
	`session_token` text NOT NULL,
	`expiration_date` numeric DEFAULT (DATETIME('now', '+7 days')) NOT NULL,
	FOREIGN KEY (`user_id`) REFERENCES `users_old`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `user_groups` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`name` text NOT NULL,
	`tenant` text NOT NULL,
	`created_at` numeric DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	`updated_at` numeric DEFAULT (CURRENT_TIMESTAMP) NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `users` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`name` text(255) NOT NULL,
	`phone_number` text(20) DEFAULT (NULL),
	`groups` text DEFAULT (NULL),
	`user_group` text DEFAULT (NULL),
	`roles` text DEFAULT (NULL),
	`activation_token` text(255) DEFAULT (NULL),
	`active` numeric DEFAULT 1 NOT NULL,
	`province` text(255) DEFAULT (NULL),
	`created_at` numeric DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	`updated_at` numeric DEFAULT (CURRENT_TIMESTAMP) NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `users_old` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`name` text(255) NOT NULL,
	`phone_number` text(20) DEFAULT (NULL),
	`groups` text DEFAULT (NULL),
	`roles` text DEFAULT (NULL),
	`activation_token` text(255) DEFAULT (NULL),
	`active` numeric DEFAULT 1 NOT NULL,
	`created_at` numeric DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	`updated_at` numeric DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	`user_group` text DEFAULT (NULL),
	`province` text(255) DEFAULT (NULL)
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `wa_messages` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` integer NOT NULL,
	`is_read` numeric DEFAULT 0 NOT NULL,
	`message` text,
	`poll_name` text(255) DEFAULT (NULL),
	`earthquake_id` integer DEFAULT (NULL),
	`updated_at` numeric NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `wa_messages_failed` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`user_id` integer NOT NULL,
	`poll_name` text(255) DEFAULT (NULL),
	`earthquake_id` integer DEFAULT (NULL),
	`reason` text,
	`updated_at` numeric DEFAULT (CURRENT_TIMESTAMP) NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `wa_users` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`name` text(255) NOT NULL,
	`phone_number` text(20) NOT NULL,
	`poll_name` text(255) DEFAULT (NULL),
	`last_sent_at` numeric,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS `idx_wa_users_phone` ON `wa_users` (`phone_number`);--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `webhooks` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`name` text(255) NOT NULL,
	`url` text NOT NULL,
	`type` text(255) NOT NULL,
	`last_sent_at` numeric,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS `idx_webhooks_name` ON `webhooks` (`name`);