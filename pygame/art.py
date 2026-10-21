        # Boss contact checks should use the readable focal hitbox rather than
        # the full sprite rectangle. This makes the attack feel intentional and
        # reduces accidental contact on the boss edges.
        boss_contact = (self.boss.weakspot() if self.boss.state == 'stunned'
                        else self.boss.body_hitbox())
        if self.boss.active and self.player.colliderect(boss_contact):
            can_stomp = self.boss.can_stomp(
                self.player, previous_bottom, self.velocity_y)
            if can_stomp and self.boss.stomp():
                self.player.bottom = self.boss.rect.top-4
                self.velocity_y = -470
                self.y = float(self.player.y)
                self.on_ground = False
                self.invincible = max(self.invincible, 0.75)
                self.audio.play('defeat')
                self.shake_camera(9.0, 0.25)
                self.spawn_burst(self.boss.rect.centerx, self.boss.rect.top,
                                 color=(255, 220, 90), count=18, radius=34)
                if self.boss.defeated:
                    self.score += self.boss.SCORE
                    self.feedback.emit(self.boss.rect.midtop,
                                       f'보스 격파! +{self.boss.SCORE}', (255, 224, 112))
                    self.progress.save(self)
                else:
                    self.feedback.emit(self.boss.rect.midtop,
                                       f'보스 타격 {self.boss.hits}/{self.boss.MAX_HITS}',
                                       (255, 224, 112))
            elif not self.invincible and self.boss.state != 'stunned':
                self.combat.hit(self.player, self.boss)
                self.feedback.emit(self.player.midtop, '보스에게 피격!', (255, 133, 125))
                self.shake_camera(11.0, 0.32)
                self.spawn_burst(self.player.centerx, self.player.centery,
                                 color=(255, 120, 110), count=16, radius=28, gravity=180)
                return
        skua_projectile_hit = (not self.invincible and self.skua_boss.active
                               and self.skua_boss.snowball_hits(self.player))
        skua_body_hit = (not self.invincible and self.skua_boss.can_damage_player()
                         and self.player.colliderect(self.skua_boss.body_hitbox()))
        if skua_projectile_hit or skua_body_hit:
            self.combat.hit(self.player, self.skua_boss)
            self.feedback.emit(self.player.midtop, '갈매기에게 피격!', (255, 133, 125))
            self.shake_camera(7.0, 0.20)
            self.spawn_burst(self.player.centerx, self.player.centery - 8,
                             color=(120, 200, 255), count=12, radius=20)
            return

        was_grounded = getattr(self, 'was_grounded', self.on_ground)
        if self.on_ground and not was_grounded and self.velocity_y >= 180:
            self.spawn_dust(self.player.centerx, self.player.bottom + 2,
                            count=10, radius=14, color=(206, 230, 240), gravity=150)
        if self.on_ground and abs(self.velocity_x) > 120:
            if not hasattr(self, 'dust_timer'):
                self.dust_timer = 0.0
            self.dust_timer -= 1.0 / 60.0
            if self.dust_timer <= 0:
                self.spawn_dust(self.player.centerx, self.player.bottom + 2,
                                count=3, radius=8, color=(206, 230, 240), gravity=150)
                self.dust_timer = 0.08
        self.was_grounded = self.on_ground

    def shake_camera(self, amount, duration=0.2):
        self.camera_shake = max(getattr(self, 'camera_shake', 0.0), amount)
        self.camera_tremor = max(getattr(self, 'camera_tremor', 0.0), duration)

    def spawn_burst(self, x, y, color=(255, 220, 110), count=12, radius=26, gravity=260):
        if not hasattr(self, 'particles'):
            self.particles = []
        self.particles.extend(burst_particles(x, y, count=count, radius=radius,
                                             color=color, gravity=gravity))

    def spawn_dust(self, x, y, color=(206, 230, 240), count=6, radius=10, gravity=150):
        if not hasattr(self, 'particles'):
            self.particles = []
        self.particles.extend(dust_particles(x, y, count=count, radius=radius,
                                            color=color, gravity=gravity))

    def update_particles(self, dt):
        if not hasattr(self, 'particles'):
            return
        for p in list(self.particles):
            p.life -= dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += p.gravity * dt
            if p.life <= 0:
                self.particles.remove(p)

    def update_camera(self, dt):
        if hasattr(self, 'camera_shake'):
            self.camera_shake = max(0.0, self.camera_shake - dt * 38.0)
        if hasattr(self, 'camera_tremor'):
            self.camera_tremor = max(0.0, self.camera_tremor - dt)

        # Call draw_particles(screen, self.particles, self.camera_x)
        # near the end of the main render pass to display the bursts.

