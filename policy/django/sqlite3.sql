BEGIN;
CREATE TABLE "okeanos_limits" (
    "lim_id" integer NOT NULL PRIMARY KEY,
    "lim_desc" varchar(45) NOT NULL
)
;
CREATE TABLE "okeanos_users" (
    "user_id" integer NOT NULL PRIMARY KEY,
    "user_name" varchar(255) NOT NULL,
    "user_credit" integer NOT NULL,
    "user_quota" integer NOT NULL,
    "user_created" date NOT NULL
)
;
CREATE TABLE "okeanos_userlimit" (
    "lim_id_id" integer NOT NULL PRIMARY KEY REFERENCES "okeanos_limits" ("lim_id"),
    "user_id_id" integer NOT NULL PRIMARY KEY REFERENCES "okeanos_users" ("user_id"),
    "ul_value" integer NOT NULL
)
;
CREATE TABLE "okeanos_flavor" (
    "flv_id" integer NOT NULL PRIMARY KEY,
    "flv_desc" varchar(255) NOT NULL,
    "flv_cost_active" integer NOT NULL,
    "flv_cost_inactive" integer NOT NULL,
    "flv_detailed" varchar(1000) NOT NULL
)
;
CREATE TABLE "okeanos_vmachine" (
    "vm_id" integer NOT NULL PRIMARY KEY,
    "vm_alias" varchar(255) NOT NULL,
    "vm_created" datetime NOT NULL,
    "vm_state" integer NOT NULL,
    "vm_started" datetime NOT NULL,
    "user_id_id" integer NOT NULL REFERENCES "okeanos_users" ("user_id"),
    "flv_id_id" integer NOT NULL REFERENCES "okeanos_flavor" ("flv_id")
)
;
CREATE TABLE "okeanos_charginglog" (
    "cl_id" integer NOT NULL PRIMARY KEY,
    "vm_id_id" integer NOT NULL REFERENCES "okeanos_vmachine" ("vm_id"),
    "cl_date" datetime NOT NULL,
    "cl_credit" integer NOT NULL,
    "cl_message" varchar(1000) NOT NULL
)
;
COMMIT;
