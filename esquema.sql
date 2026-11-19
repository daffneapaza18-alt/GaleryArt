PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS obra_grupo;
DROP TABLE IF EXISTS obra;
DROP TABLE IF EXISTS estilo;
DROP TABLE IF EXISTS grupo;

CREATE TABLE estilo (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre  TEXT NOT NULL UNIQUE COLLATE NOCASE
            CHECK (length(trim(nombre)) > 0)
);

CREATE TABLE grupo (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre  TEXT NOT NULL UNIQUE COLLATE NOCASE
            CHECK (length(trim(nombre)) > 0)
);

CREATE TABLE obra (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo       TEXT    NOT NULL CHECK (length(trim(titulo)) > 0),
    artista      TEXT    NOT NULL DEFAULT 'Anónimo',
    fecha        TEXT    NOT NULL,
    imagen       BLOB    NOT NULL,
    ancho        INTEGER NOT NULL,
    alto         INTEGER NOT NULL,
    peso_bytes   INTEGER NOT NULL DEFAULT 0,
    descripcion  TEXT    NOT NULL DEFAULT '',
    favorita     INTEGER NOT NULL DEFAULT 0 CHECK (favorita IN (0, 1)),
    estilo_id    INTEGER,
    FOREIGN KEY (estilo_id) REFERENCES estilo (id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

CREATE TABLE obra_grupo (
    obra_id   INTEGER NOT NULL,
    grupo_id  INTEGER NOT NULL,
    PRIMARY KEY (obra_id, grupo_id),
    FOREIGN KEY (obra_id)  REFERENCES obra  (id) ON DELETE CASCADE,
    FOREIGN KEY (grupo_id) REFERENCES grupo (id) ON DELETE CASCADE
);
